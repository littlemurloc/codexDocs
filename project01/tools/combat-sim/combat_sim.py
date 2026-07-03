from __future__ import annotations

from dataclasses import dataclass, field
import argparse
import copy
import random


TICK = 0.5
MAX_TIME = 90.0
SLOT_ORDER = {"front": 0, "skirmish": 1, "mid": 2, "back": 3, "support": 4}


@dataclass
class Status:
    kind: str
    value: float
    duration: float
    source: str
    stacks: int = 1


@dataclass
class Item:
    name: str
    keyword: str
    effect: str
    value: float


@dataclass
class Unit:
    name: str
    side: str
    role: str
    max_hp: float
    atk: float
    armor: float
    interval: float
    slot: str
    skills: list[str] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    hp: float = 0
    shield: float = 0
    attack_cd: float = 0
    skill_cd: dict[str, float] = field(default_factory=dict)
    statuses: list[Status] = field(default_factory=list)
    once_flags: set[str] = field(default_factory=set)
    dead_at: float | None = None

    def __post_init__(self) -> None:
        self.hp = self.max_hp
        self.skill_cd = {skill: 0 for skill in self.skills}

    @property
    def alive(self) -> bool:
        return self.hp > 0


class Battle:
    def __init__(self, heroes: list[Unit], enemies: list[Unit], seed: int = 7, preps: list[str] | None = None):
        self.rng = random.Random(seed)
        self.units = heroes + enemies
        self.preps = set(preps or [])
        self.time = 0.0
        self.log: list[str] = []
        self.stats = {
            "damage": {},
            "taken": {},
            "healing": {},
            "shield_absorb": {},
            "skill_casts": {},
            "keyword_damage": {},
            "counter_triggers": {},
            "stun_time": {},
            "morale_time": {},
            "armor_break_time": {},
            "item_contrib": {},
            "prep_triggers": {},
            "deaths": [],
        }

    def living(self, side: str) -> list[Unit]:
        return [u for u in self.units if u.side == side and u.alive]

    def enemies_of(self, unit: Unit) -> list[Unit]:
        return self.living("enemy" if unit.side == "player" else "player")

    def allies_of(self, unit: Unit) -> list[Unit]:
        return self.living(unit.side)

    def run(self) -> dict:
        while self.time < MAX_TIME and self.living("player") and self.living("enemy"):
            self.tick_statuses()
            self.check_deaths()
            for unit in list(self.units):
                if unit.alive:
                    self.act(unit)
            self.check_deaths()
            self.time += TICK

        if self.living("player") and not self.living("enemy"):
            result = "win"
        elif self.living("enemy") and not self.living("player"):
            result = "loss"
        else:
            result = "timeout"
        player_units = [u for u in self.units if u.side == "player"]
        player_hp_pct = sum(max(0, u.hp) for u in player_units) / sum(u.max_hp for u in player_units)
        player_deaths = [u.name for u in player_units if not u.alive]
        return {
            "result": result,
            "time": round(self.time, 1),
            "stats": self.stats,
            "survivors": {u.name: round(u.hp, 1) for u in self.units if u.alive},
            "player_hp_pct": round(player_hp_pct * 100, 1),
            "player_deaths": player_deaths,
        }

    def act(self, unit: Unit) -> None:
        self.check_passives(unit)
        if self.has_status(unit, "stun"):
            return
        for skill in unit.skills:
            unit.skill_cd[skill] = max(0, unit.skill_cd.get(skill, 0) - TICK)
        unit.attack_cd = max(0, unit.attack_cd - TICK)

        for skill in unit.skills:
            if unit.skill_cd.get(skill, 0) <= 0 and self.cast_skill(unit, skill):
                cooldown = skill_cooldown(skill)
                if "技能预热" in self.preps and f"技能预热:{unit.name}" not in unit.once_flags:
                    unit.once_flags.add(f"技能预热:{unit.name}")
                    cooldown *= 0.65
                    self.record_prep("技能预热")
                unit.skill_cd[skill] = cooldown
                self.stats["skill_casts"][f"{unit.name}:{skill}"] = (
                    self.stats["skill_casts"].get(f"{unit.name}:{skill}", 0) + 1
                )
                return

        if unit.attack_cd <= 0:
            target = self.select_target(unit, "normal")
            if target:
                self.deal_damage(unit, target, unit.atk, "normal", "physical")
                unit.attack_cd = self.attack_interval(unit)

    def cast_skill(self, unit: Unit, skill: str) -> bool:
        enemies = self.enemies_of(unit)
        allies = self.allies_of(unit)
        if not enemies and skill not in {"铁壁", "据桥死守", "魏武号令", "整军", "坚阵令"}:
            return False

        if skill == "青龙斩":
            self.deal_damage(unit, self.select_target(unit, "front"), unit.atk * 1.3, skill, "physical")
        elif skill == "义刃":
            target = self.select_target(unit, "front")
            self.deal_damage(unit, target, unit.atk * 0.9, skill, "physical")
            self.add_armor_break(target, 6, 5, unit.name)
        elif skill == "破阵横扫":
            for target in self.select_many(unit, "front_area", 3):
                self.deal_damage(unit, target, unit.atk * 0.8, skill, "physical")
                self.add_armor_break(target, 4, 4, unit.name)
        elif skill == "当阳怒吼":
            for target in self.select_many(unit, "front_area", 2):
                self.deal_damage(unit, target, unit.atk * 0.8, skill, "physical")
                self.add_status(target, Status("stun", 0, 1.0, unit.name))
        elif skill == "铁壁":
            self.add_shield(unit, 220, 6, unit.name)
        elif skill == "断喝":
            for target in self.select_many(unit, "front_area", 2):
                self.add_status(target, Status("atk_down", 0.15, 5, unit.name))
        elif skill == "借东风":
            for target in enemies:
                self.add_burn(unit, target, 1, 6)
        elif skill == "火计":
            target = self.rng.choice(enemies)
            self.deal_damage(unit, target, unit.atk, skill, "magic")
            self.add_burn(unit, target, 1, 5)
        elif skill == "八阵定军":
            for target in self.select_many(unit, "front_area", 2):
                self.add_status(target, Status("stun", 0, 1.5, unit.name))
        elif skill == "魏武号令":
            for ally in allies:
                self.add_status(ally, Status("morale_atk", 0.12, 6 + self.item_bonus(unit, "士气持续"), unit.name))
        elif skill == "挟令压制":
            target = self.select_target(unit, "highest_attack")
            self.deal_damage(unit, target, unit.atk * 0.8, skill, "physical")
            self.add_status(target, Status("atk_down", 0.12, 5, unit.name))
        elif skill == "整军":
            target = min(allies, key=lambda u: u.hp / u.max_hp)
            self.heal(unit, target, 140 * (1 + self.item_bonus(unit, "治疗量")))
        elif skill == "坚阵令":
            target = min(allies, key=lambda u: SLOT_ORDER.get(u.slot, 9))
            self.add_shield(target, 180, 6, unit.name)
        elif skill == "独目狂怒":
            target = self.select_target(unit, "front")
            amount = unit.atk * (1.1 + (0.6 if unit.shield > 0 else 0))
            self.deal_damage(unit, target, amount, skill, "physical")
        elif skill == "碎盾震击":
            if unit.shield <= 0:
                return False
            amount = unit.shield * 0.6
            unit.shield = 0
            for target in self.select_many(unit, "front_area", 2):
                self.deal_damage(unit, target, amount, skill, "physical")
        elif skill == "连弩急射":
            self.deal_damage(unit, self.select_target(unit, "lowest_hp"), unit.atk * 0.9, skill, "physical")
        elif skill == "裂帛箭":
            target = self.select_target(unit, "front")
            self.deal_damage(unit, target, unit.atk * 0.7, skill, "physical")
            self.add_bleed(unit, target, 2, 6)
        elif skill == "追命":
            target = self.select_target(unit, "lowest_hp")
            if target.hp / target.max_hp > 0.35:
                return False
            self.deal_damage(unit, target, unit.atk * 1.8, skill, "physical")
        elif skill == "赤壁火海":
            for target in enemies:
                self.deal_damage(unit, target, unit.atk * 0.8, skill, "magic")
                self.add_burn(unit, target, 1, 6)
        elif skill == "连环火":
            burn_targets = [e for e in enemies if self.status_stacks(e, "burn") > 0]
            target = burn_targets[0] if burn_targets else self.select_target(unit, "front")
            self.deal_damage(unit, target, unit.atk * 1.2, skill, "magic")
            if self.status_stacks(target, "burn") > 0 and enemies:
                self.add_burn(unit, self.rng.choice(enemies), 1, 5)
        elif skill == "火墙":
            for target in self.select_many(unit, "front_area", 3):
                self.add_burn(unit, target, 2, 5)
        elif skill == "方天突刺":
            self.deal_damage(unit, self.select_target(unit, "highest_attack"), unit.atk * 1.2, skill, "physical")
        elif skill == "无双连斩":
            target = self.select_target(unit, "front")
            for _ in range(3):
                self.deal_damage(unit, target, unit.atk * 0.55, skill, "physical")
        elif skill == "威压":
            target = self.select_target(unit, "front")
            self.deal_damage(unit, target, unit.atk * 0.8, skill, "physical")
            self.add_status(target, Status("stun", 0, 1.0, unit.name))
        elif skill == "穿云箭":
            target = self.select_target(unit, "lowest_armor")
            self.deal_damage(unit, target, unit.atk * 1.25, skill, "physical")
        elif skill == "后排齐射":
            for target in self.select_many(unit, "lowest_armor", 2):
                self.deal_damage(unit, target, unit.atk * 0.9, skill, "physical")
        elif skill == "重斩":
            self.deal_damage(unit, self.select_target(unit, "front"), unit.atk * 1.5, skill, "physical")
        elif skill == "破胆":
            self.add_status(self.select_target(unit, "front"), Status("atk_down", 0.12, 5, unit.name))
        elif skill == "符令震慑":
            self.add_status(self.select_target(unit, "front"), Status("stun", 0, 1.2, unit.name))
        elif skill == "乱心符":
            target = self.select_target(unit, "highest_attack")
            self.deal_damage(unit, target, unit.atk * 0.9, skill, "magic")
            self.add_status(target, Status("stun", 0, 0.8, unit.name))
        elif skill in {"鼓舞", "符令鼓舞"}:
            bonus = 0.10 if skill == "鼓舞" else 0.12
            for ally in allies:
                self.add_status(ally, Status("morale_atk", bonus, 5, unit.name))
        elif skill == "聚众":
            self.units.extend([make_enemy("黄巾步卒", f"召唤步卒{int(self.time)}-{i}") for i in range(2)])
        elif skill == "符令落雷":
            self.deal_damage(unit, self.select_target(unit, "lowest_armor"), unit.atk * 1.1, skill, "magic")
        else:
            return False
        return True

    def tick_statuses(self) -> None:
        for unit in self.units:
            if not unit.alive:
                continue
            for status in list(unit.statuses):
                if status.kind == "bleed":
                    self.direct_dot(unit, 18 * status.stacks * TICK, "流血", status.source)
                elif status.kind == "burn":
                    armor = max(0, self.effective_armor(unit)) * 0.5
                    amount = 14 * status.stacks * TICK * 100 / (100 + armor)
                    amount *= 1 + self.source_burn_bonus(status.source)
                    self.direct_dot(unit, amount, "灼烧", status.source)
                if status.kind == "stun":
                    self.stats["stun_time"][unit.name] = self.stats["stun_time"].get(unit.name, 0) + TICK
                elif status.kind == "morale_atk":
                    self.stats["morale_time"][unit.name] = self.stats["morale_time"].get(unit.name, 0) + TICK
                elif status.kind == "armor_break":
                    self.stats["armor_break_time"][unit.name] = self.stats["armor_break_time"].get(unit.name, 0) + TICK
                status.duration -= TICK
                if status.kind == "shield_timer" and status.duration <= 0:
                    unit.shield = max(0, unit.shield - status.value)
            unit.statuses = [s for s in unit.statuses if s.duration > 0]

    def check_passives(self, unit: Unit) -> None:
        if unit.name == "张飞" and "据桥死守" in unit.skills:
            if unit.hp / unit.max_hp < 0.4 and "据桥死守" not in unit.once_flags:
                unit.once_flags.add("据桥死守")
                self.add_shield(unit, 300, 6, unit.name)
        if unit.name == "夏侯惇" and "拔矢啖睛" in unit.skills:
            if unit.hp / unit.max_hp < 0.5 and "拔矢啖睛" not in unit.once_flags:
                unit.once_flags.add("拔矢啖睛")
                self.add_shield(unit, 180, 6, unit.name)
                self.heal(unit, unit, 120)

    def check_deaths(self) -> None:
        for unit in self.units:
            if unit.hp <= 0 and unit.dead_at is None:
                unit.dead_at = self.time
                self.stats["deaths"].append((round(self.time, 1), unit.name, unit.side))
                for src in {s.source for s in unit.statuses if s.kind == "burn"}:
                    source = self.find_unit(src)
                    if source and ("火势蔓延" in source.skills or self.has_prep("火势牵连")):
                        chance = (0.5 if "火势蔓延" in source.skills else 0.25) + self.item_bonus(source, "灼烧扩散概率")
                        if self.rng.random() < chance:
                            candidates = [e for e in self.living(unit.side) if e.name != unit.name]
                            if candidates:
                                if self.has_prep("火势牵连"):
                                    self.record_prep("火势牵连")
                                self.add_burn(source, self.rng.choice(candidates), 1, 4)

    def deal_damage(self, source: Unit, target: Unit | None, amount: float, tag: str, dtype: str) -> None:
        if not target or not target.alive:
            return
        amount *= self.atk_multiplier(source)
        if tag in {"连弩急射", "无双连斩"}:
            amount *= 1 + self.item_bonus(source, "连击追加伤害")
        if "破釜沉舟" in self.preps and source.side == "player" and source.hp / source.max_hp < 0.4:
            amount *= 1.18
            self.record_prep("破釜沉舟")
        if tag == "normal" and self.status_stacks(target, "bleed") > 0 and "凝神" in source.skills:
            amount *= 1.2
        if tag == "normal" and self.status_stacks(target, "bleed") > 0:
            amount *= 1 + self.item_bonus(source, "攻击流血")
        if self.status_stacks(target, "burn") > 0 and source.name == "周瑜":
            amount *= 1.18
        if self.status_stacks(target, "armor_break") > 0:
            amount *= 1 + self.item_bonus(source, "攻击破甲")
        if target.hp / target.max_hp <= 0.35 and (
            self.status_stacks(target, "bleed") > 0 or self.status_stacks(target, "armor_break") > 0
        ):
            amount *= 1 + self.item_bonus(source, "低血终结")
        if source.name == "吕布":
            lost = 1 - source.hp / source.max_hp
            amount *= 1 + min(0.18, int(lost * 10) * 0.03)
        if dtype in {"physical", "magic"}:
            armor = self.effective_armor(target)
            amount *= 100 / (100 + max(0, armor))
        self.apply_damage(source, target, amount, tag)
        self.try_weakpoint_barrage(target)
        if tag in {"normal", "连弩急射", "无双连斩"} and target.alive:
            burn_chance = self.item_bonus(source, "灼烧接入概率")
            if burn_chance > 0 and self.rng.random() < burn_chance:
                self.add_burn(source, target, 1, 3)
        if tag in {"连弩急射", "无双连斩"} and target.alive:
            bleed_stacks = int(self.item_bonus(source, "连击流血"))
            if bleed_stacks > 0:
                self.add_bleed(source, target, bleed_stacks, 5)
        self.try_counter(target, source)

    def apply_damage(self, source: Unit, target: Unit, amount: float, tag: str) -> None:
        had_shield = target.shield > 0
        if target.shield > 0:
            absorbed = min(target.shield, amount)
            target.shield -= absorbed
            amount -= absorbed
            self.stats["shield_absorb"][target.name] = self.stats["shield_absorb"].get(target.name, 0) + absorbed
            if had_shield and target.shield <= 0:
                recover = self.item_bonus(target, "破盾回复")
                if recover > 0:
                    self.heal(target, target, target.max_hp * recover)
                if "破盾回击" in self.preps and target.side == "player" and "破盾回击" not in target.once_flags:
                    target.once_flags.add("破盾回击")
                    self.record_prep("破盾回击")
                    self.deal_damage(target, source, target.atk * 0.65, "破盾回击", "physical")
        if amount > 0:
            target.hp -= amount
            self.stats["damage"][source.name] = self.stats["damage"].get(source.name, 0) + amount
            self.stats["taken"][target.name] = self.stats["taken"].get(target.name, 0) + amount
            self.stats["keyword_damage"][tag] = self.stats["keyword_damage"].get(tag, 0) + amount

    def direct_dot(self, target: Unit, amount: float, tag: str, source_name: str) -> None:
        source = self.find_unit(source_name)
        if not source or not target.alive:
            return
        self.apply_damage(source, target, amount, tag)

    def add_status(self, target: Unit | None, status: Status) -> None:
        if target and target.alive:
            target.statuses.append(status)

    def add_armor_break(self, target: Unit | None, amount: float, duration: float, source: str) -> None:
        if not target:
            return
        duration += self.item_bonus(self.find_unit(source), "破甲持续")
        current = sum(s.value for s in target.statuses if s.kind == "armor_break")
        if current >= 14:
            return
        target.statuses.append(Status("armor_break", min(amount, 14 - current), duration, source))

    def add_bleed(self, source: Unit, target: Unit | None, stacks: int, duration: float) -> None:
        if not target:
            return
        stacks += int(self.item_bonus(source, "流血附加"))
        max_stacks = 6 + int(self.item_bonus(source, "流血层数"))
        current = self.status_stacks(target, "bleed")
        add = max(0, min(stacks, max_stacks - current))
        if add:
            target.statuses.append(Status("bleed", 18, duration, source.name, add))

    def add_burn(self, source: Unit, target: Unit | None, stacks: int, duration: float) -> None:
        if not target:
            return
        duration += self.item_bonus(source, "灼烧持续")
        current = self.status_stacks(target, "burn")
        add = max(0, min(stacks, 5 - current))
        if add:
            target.statuses.append(Status("burn", 14, duration, source.name, add))

    def add_shield(self, target: Unit, amount: float, duration: float, source: str) -> None:
        source_unit = self.find_unit(source)
        amount *= 1 + self.item_bonus(source_unit or target, "护盾量")
        target.shield += amount
        target.statuses.append(Status("shield_timer", amount, duration, source))
        if target.name == "夏侯惇":
            target.statuses.append(Status("counter_bonus", 0.35, 6, target.name))
            target.statuses.append(Status("guarded_counter", 0, 6, target.name))

    def heal(self, source: Unit, target: Unit, amount: float) -> None:
        if "破釜沉舟" in self.preps and target.side == "player":
            amount *= 0.75
        before = target.hp
        target.hp = min(target.max_hp, target.hp + amount)
        done = target.hp - before
        self.stats["healing"][source.name] = self.stats["healing"].get(source.name, 0) + done
        if target.hp / target.max_hp < 0.4 and self.item_bonus(source, "治疗低血护盾") > 0:
            self.add_shield(target, 80, 5, source.name)

    def try_counter(self, defender: Unit, attacker: Unit) -> None:
        if not defender.alive or not attacker.alive or attacker.slot in {"mid", "back", "support"}:
            return
        chance = 0
        damage = 0
        if defender.name == "关羽" and "偃月反击" in defender.skills:
            chance = 0.25
            damage = defender.atk * 0.55
        elif defender.name == "夏侯惇" and (defender.shield > 0 or self.has_status(defender, "guarded_counter")):
            chance = 0.45
            bonus = 1 + self.status_value(defender, "counter_bonus") + self.item_bonus(defender, "护盾反击")
            damage = defender.atk * 0.75 * bonus
        if chance and self.rng.random() < chance:
            self.stats["counter_triggers"][defender.name] = self.stats["counter_triggers"].get(defender.name, 0) + 1
            self.deal_damage(defender, attacker, damage, "反击", "physical")
            recover = self.item_bonus(defender, "反击回复")
            if recover > 0:
                self.heal(defender, defender, defender.max_hp * recover)

    def select_target(self, unit: Unit, rule: str) -> Unit | None:
        enemies = self.enemies_of(unit)
        if not enemies:
            return None
        if rule in {"normal", "front"}:
            return sorted(enemies, key=lambda u: (SLOT_ORDER.get(u.slot, 9), u.hp / u.max_hp))[0]
        if rule == "lowest_hp":
            return min(enemies, key=lambda u: u.hp / u.max_hp)
        if rule == "highest_attack":
            return max(enemies, key=lambda u: u.atk)
        if rule == "lowest_armor":
            return min(enemies, key=lambda u: (u.armor, u.hp / u.max_hp))
        return enemies[0]

    def select_many(self, unit: Unit, rule: str, count: int) -> list[Unit]:
        enemies = self.enemies_of(unit)
        if rule == "lowest_armor":
            return sorted(enemies, key=lambda u: (u.armor, u.hp / u.max_hp))[:count]
        return sorted(enemies, key=lambda u: SLOT_ORDER.get(u.slot, 9))[:count]

    def effective_armor(self, unit: Unit) -> float:
        return max(0, unit.armor - sum(s.value for s in unit.statuses if s.kind == "armor_break"))

    def attack_interval(self, unit: Unit) -> float:
        return unit.interval

    def atk_multiplier(self, unit: Unit) -> float:
        bonus = sum(s.value for s in unit.statuses if s.kind == "morale_atk")
        penalty = sum(s.value for s in unit.statuses if s.kind == "atk_down")
        return max(0.2, 1 + bonus - penalty)

    def status_stacks(self, unit: Unit, kind: str) -> int:
        return sum(s.stacks for s in unit.statuses if s.kind == kind)

    def status_value(self, unit: Unit, kind: str) -> float:
        return sum(s.value for s in unit.statuses if s.kind == kind)

    def has_status(self, unit: Unit, kind: str) -> bool:
        return any(s.kind == kind for s in unit.statuses)

    def item_bonus(self, unit: Unit | None, effect: str) -> float:
        if not unit:
            return 0
        bonus = sum(item.value for item in unit.items if item.effect == effect)
        if any(item.name == "风火锦囊" for item in unit.items) and effect == "士气持续":
            bonus += 2
        return bonus

    def has_prep(self, prep: str) -> bool:
        return prep in self.preps

    def record_prep(self, prep: str) -> None:
        self.stats["prep_triggers"][prep] = self.stats["prep_triggers"].get(prep, 0) + 1

    def try_weakpoint_barrage(self, target: Unit) -> None:
        if "弱点齐射" not in self.preps or target.side != "enemy" or target.role != "Boss":
            return
        if target.hp / target.max_hp > 0.5 or "弱点齐射" in target.once_flags:
            return
        target.once_flags.add("弱点齐射")
        self.record_prep("弱点齐射")
        for ally in self.living("player"):
            for skill in ally.skill_cd:
                ally.skill_cd[skill] = max(0, ally.skill_cd[skill] - 2.0)

    def source_burn_bonus(self, source_name: str) -> float:
        source = self.find_unit(source_name)
        return self.item_bonus(source, "灼烧伤害")

    def find_unit(self, name: str) -> Unit | None:
        for unit in self.units:
            if unit.name == name:
                return unit
        return None


def skill_cooldown(skill: str) -> float:
    cds = {
        "青龙斩": 5, "义刃": 8, "破阵横扫": 11,
        "当阳怒吼": 8, "铁壁": 10, "断喝": 12,
        "借东风": 12, "火计": 6, "八阵定军": 14,
        "魏武号令": 12, "挟令压制": 9, "整军": 10, "坚阵令": 13,
        "独目狂怒": 9, "碎盾震击": 11,
        "连弩急射": 5, "裂帛箭": 7, "追命": 10,
        "赤壁火海": 13, "连环火": 8, "火墙": 10,
        "方天突刺": 6, "无双连斩": 9, "威压": 12,
        "重斩": 8, "破胆": 12, "穿云箭": 5, "后排齐射": 8,
        "符令震慑": 9, "乱心符": 10, "鼓舞": 12,
        "聚众": 14, "符令鼓舞": 12, "符令落雷": 10,
    }
    return cds.get(skill, 999)


HEROES = {
    "关羽": dict(role="猛将", max_hp=1150, atk=65, armor=16, interval=1.7, slot="front",
               skills=["青龙斩", "义刃", "偃月反击", "破阵横扫"]),
    "张飞": dict(role="猛将", max_hp=1350, atk=48, armor=22, interval=1.9, slot="front",
               skills=["当阳怒吼", "铁壁", "断喝", "据桥死守"]),
    "诸葛亮": dict(role="智将", max_hp=700, atk=68, armor=6, interval=1.9, slot="mid",
                skills=["借东风", "火计", "八阵定军", "火势蔓延"]),
    "曹操": dict(role="辅将", max_hp=900, atk=45, armor=11, interval=1.7, slot="support",
               skills=["魏武号令", "挟令压制", "整军", "坚阵令"]),
    "夏侯惇": dict(role="猛将", max_hp=1250, atk=58, armor=18, interval=1.8, slot="front",
                skills=["刚烈之身", "独目狂怒", "拔矢啖睛", "碎盾震击"]),
    "孙尚香": dict(role="敏将", max_hp=760, atk=72, armor=8, interval=1.3, slot="skirmish",
                skills=["连弩急射", "裂帛箭", "追命", "凝神"]),
    "周瑜": dict(role="智将", max_hp=720, atk=74, armor=6, interval=1.8, slot="mid",
               skills=["赤壁火海", "连环火", "火墙", "火势专注"]),
    "吕布": dict(role="敏将", max_hp=1000, atk=82, armor=12, interval=1.4, slot="skirmish",
               skills=["方天突刺", "血战", "无双连斩", "威压"]),
}

ITEMS = {
    # Official 12-piece MVP equipment pool; effects are simulator proxies for direction validation.
    "玄铁盾": Item("玄铁盾", "护盾", "护盾量", 0.25),
    "虎纹重甲": Item("虎纹重甲", "反击", "护盾反击", 0.25),
    "裂阵铁钩": Item("裂阵铁钩", "破甲", "破甲持续", 3),
    "还血护符": Item("还血护符", "续航", "反击回复", 0.035),
    "赤焰羽扇": Item("赤焰羽扇", "灼烧", "灼烧伤害", 0.20),
    "燎原石": Item("燎原石", "灼烧", "灼烧接入概率", 0.18),
    "连环火令": Item("连环火令", "灼烧", "灼烧扩散概率", 0.20),
    "风火锦囊": Item("风火锦囊", "士气", "灼烧持续", 1),
    "血纹匕首": Item("血纹匕首", "流血", "流血附加", 1),
    "裂骨箭囊": Item("裂骨箭囊", "流血", "连击流血", 1),
    "白马镫": Item("白马镫", "连击", "连击追加伤害", 0.18),
    "断首符": Item("断首符", "斩杀", "低血终结", 0.18),
}

ENEMIES = {
    "黄巾步卒": dict(role="小怪", max_hp=260, atk=32, armor=4, interval=1.6, slot="front", skills=[]),
    "西凉盾兵": dict(role="盾兵", max_hp=950, atk=48, armor=34, interval=1.8, slot="front", skills=[]),
    "西凉刀兵": dict(role="近战", max_hp=420, atk=40, armor=10, interval=1.6, slot="front", skills=[]),
    "西凉弓骑": dict(role="远程", max_hp=380, atk=58, armor=5, interval=1.5, slot="mid", skills=["穿云箭", "后排齐射"]),
    "护卫兵": dict(role="前排", max_hp=500, atk=36, armor=14, interval=1.8, slot="front", skills=[]),
    "黄巾祭酒": dict(role="控制", max_hp=500, atk=34, armor=6, interval=1.9, slot="mid", skills=["符令震慑", "乱心符", "鼓舞"]),
    "华雄先锋": dict(role="精英", max_hp=1800, atk=68, armor=18, interval=1.5, slot="front", skills=["重斩", "破胆"]),
    "黄巾渠帅": dict(role="Boss", max_hp=2800, atk=62, armor=16, interval=1.8, slot="front", skills=["聚众", "符令鼓舞", "符令落雷"]),
}

SCENARIOS = {
    "小怪群": ["黄巾步卒"] * 6,
    "高甲前排": ["西凉盾兵"] * 2,
    "前后排压力": ["西凉刀兵", "西凉刀兵", "西凉弓骑", "西凉弓骑"],
    "控制压力": ["护卫兵", "护卫兵", "黄巾祭酒", "黄巾祭酒"],
    "单体精英": ["华雄先锋"],
    "Boss雏形": ["黄巾渠帅", "黄巾步卒", "黄巾步卒"],
}

TEAMS = {
    "张飞+孙尚香": (["张飞", "孙尚香"], {"张飞": ["玄铁盾"], "孙尚香": ["血纹匕首", "裂骨箭囊"]}),
    "关羽+孙尚香": (["关羽", "孙尚香"], {"关羽": ["裂阵铁钩"], "孙尚香": ["血纹匕首", "裂骨箭囊"]}),
    "张飞+周瑜": (["张飞", "周瑜"], {"张飞": ["玄铁盾"], "周瑜": ["赤焰羽扇"]}),
    "夏侯惇+曹操": (["夏侯惇", "曹操"], {"夏侯惇": ["虎纹重甲", "还血护符"], "曹操": ["风火锦囊"]}),
    "吕布+曹操": (["吕布", "曹操"], {"吕布": ["裂骨箭囊", "断首符"], "曹操": ["风火锦囊"]}),
    "诸葛亮+周瑜": (["诸葛亮", "周瑜"], {"诸葛亮": ["连环火令", "风火锦囊"], "周瑜": ["赤焰羽扇", "燎原石"]}),
    "张飞+夏侯惇": (["张飞", "夏侯惇"], {"张飞": ["玄铁盾"], "夏侯惇": ["虎纹重甲"]}),
    "关羽+吕布": (["关羽", "吕布"], {"关羽": ["裂阵铁钩"], "吕布": ["白马镫", "断首符"]}),
}

PREPS = ["破盾回击", "火势牵连", "弱点齐射", "技能预热", "破釜沉舟", "重新侦察"]


def make_hero(name: str, items: list[str] | None = None) -> Unit:
    data = copy.deepcopy(HEROES[name])
    unit = Unit(name=name, side="player", **data)
    unit.items = [ITEMS[i] for i in (items or [])]
    return unit


def make_enemy(kind: str, name: str | None = None) -> Unit:
    data = copy.deepcopy(ENEMIES[kind])
    return Unit(name=name or kind, side="enemy", **data)


def format_result(team_name: str, scenario_name: str, result: dict) -> str:
    stats = result["stats"]
    damage = stats["damage"]
    keyword = stats["keyword_damage"]
    top_damage = sorted(((k, v) for k, v in damage.items() if k in HEROES), key=lambda x: -x[1])[:4]
    return (
        f"{team_name:<12} vs {scenario_name:<8} | {result['result']:<7} | "
        f"{result['time']:>5}s | "
        f"余血 {result['player_hp_pct']:>5.1f}% | 阵亡 {len(result['player_deaths'])} | "
        f"伤害 {fmt_pairs(top_damage)} | "
        f"护盾 {round(sum(stats['shield_absorb'].values()), 1):>6} | "
        f"治疗 {round(sum(stats['healing'].values()), 1):>6} | "
        f"流血 {round(keyword.get('流血', 0), 1):>6} | 灼烧 {round(keyword.get('灼烧', 0), 1):>6} | "
        f"反击 {round(keyword.get('反击', 0), 1):>6}"
    )


def diagnose_result(team_name: str, scenario_name: str, result: dict) -> list[str]:
    stats = result["stats"]
    keyword = stats["keyword_damage"]
    notes: list[str] = []
    hp = result["player_hp_pct"]
    deaths = len(result["player_deaths"])
    battle_time = result["time"]

    if result["result"] == "loss":
        notes.append("失败：该队伍缺少本试题所需闭环")
    elif result["result"] == "timeout":
        notes.append("超时：输出或清场效率不足")
    elif deaths > 0:
        notes.append("险胜：出现阵亡，容错偏低")
    elif hp < 35:
        notes.append("低余血胜利：压力有效，但稳定性不足")
    elif hp > 80 and battle_time < 12:
        notes.append("轻松通过：该试题对该队伍压力偏低")

    if scenario_name == "小怪群":
        if keyword.get("灼烧", 0) > 500:
            notes.append("清杂优势：灼烧/范围收益明显")
        elif battle_time > 22:
            notes.append("清杂偏慢：缺少群体处理")
    elif scenario_name == "高甲前排":
        armor_break = sum(stats["armor_break_time"].values())
        bleed = keyword.get("流血", 0)
        if armor_break > 8 or bleed > 120:
            notes.append("高甲反制成立：破甲或流血有效")
        elif battle_time > 22:
            notes.append("高甲处理偏慢：缺少破甲/真实持续伤害")
    elif scenario_name == "前后排压力":
        if hp < 55:
            notes.append("后排压力有效：低甲单位承压明显")
        if battle_time > 25:
            notes.append("后排处理偏慢：输出触达或清场不足")
    elif scenario_name == "控制压力":
        stun_taken = sum(v for name, v in stats["stun_time"].items() if name in HEROES)
        if stun_taken > 5:
            notes.append("控制压力有效：我方被控时间较高")
        if hp > 80 and battle_time < 15:
            notes.append("控制试题偏弱：未明显影响战斗节奏")
    elif scenario_name == "单体精英":
        if keyword.get("流血", 0) > 250 or sum(stats["armor_break_time"].values()) > 8:
            notes.append("精英反制成立：持续伤害/破甲贡献明显")
        elif battle_time > 28:
            notes.append("单体输出偏慢：精英处理压力较高")
    elif scenario_name == "Boss雏形":
        if result["result"] == "win" and hp > 35:
            notes.append("Boss 闭环成立：清杂与单体压力都能处理")
        elif result["result"] == "win":
            notes.append("Boss 勉强通过：闭环成立但容错低")
        else:
            notes.append("Boss 闭环缺口：清杂、续航或单体压制不足")

    if not notes:
        notes.append("表现中性：需要结合对照组判断")
    return notes


def format_diagnosis(team_name: str, scenario_name: str, result: dict) -> str:
    notes = "；".join(diagnose_result(team_name, scenario_name, result))
    return f"{format_result(team_name, scenario_name, result)} | 诊断 {notes}"


def fmt_pairs(pairs: list[tuple[str, float]]) -> str:
    return ", ".join(f"{k}:{round(v)}" for k, v in pairs)


def simulate(team_name: str, scenario_name: str, use_items: bool = True, preps: list[str] | None = None) -> dict:
    hero_names, item_map = TEAMS[team_name]
    enemy_kinds = SCENARIOS[scenario_name]
    heroes = [make_hero(h, item_map.get(h, []) if use_items else []) for h in hero_names]
    enemies = [make_enemy(e, f"{e}{idx + 1}") for idx, e in enumerate(enemy_kinds)]
    return Battle(heroes, enemies, preps=preps).run()


def metric(result: dict, key: str) -> float:
    stats = result["stats"]
    keyword = stats["keyword_damage"]
    if key == "prep_damage":
        return sum(keyword.get(prep, 0) for prep in PREPS)
    if key == "shield":
        return sum(stats["shield_absorb"].values())
    if key == "healing":
        return sum(stats["healing"].values())
    if key in {"流血", "灼烧", "反击"}:
        return keyword.get(key, 0)
    if key == "armor_break":
        return sum(stats["armor_break_time"].values())
    if key == "morale":
        return sum(stats["morale_time"].values())
    return 0


def format_compare(team_name: str, scenario_name: str, with_items: dict, no_items: dict) -> str:
    time_delta = no_items["time"] - with_items["time"]
    result_shift = f"{no_items['result']}->{with_items['result']}"
    return (
        f"{team_name:<12} vs {scenario_name:<8} | {result_shift:<13} | "
        f"省时 {time_delta:>5.1f}s | "
        f"护盾差 {metric(with_items, 'shield') - metric(no_items, 'shield'):>7.1f} | "
        f"治疗差 {metric(with_items, 'healing') - metric(no_items, 'healing'):>7.1f} | "
        f"破甲差 {metric(with_items, 'armor_break') - metric(no_items, 'armor_break'):>7.1f} | "
        f"士气差 {metric(with_items, 'morale') - metric(no_items, 'morale'):>7.1f} | "
        f"流血差 {metric(with_items, '流血') - metric(no_items, '流血'):>7.1f} | "
        f"灼烧差 {metric(with_items, '灼烧') - metric(no_items, '灼烧'):>7.1f} | "
        f"反击差 {metric(with_items, '反击') - metric(no_items, '反击'):>7.1f}"
    )


def format_prep_compare(team_name: str, scenario_name: str, prep_name: str, with_prep: dict, no_prep: dict) -> str:
    time_delta = no_prep["time"] - with_prep["time"]
    result_shift = f"{no_prep['result']}->{with_prep['result']}"
    prep_triggers = with_prep["stats"]["prep_triggers"].get(prep_name, 0)
    return (
        f"{prep_name:<6} | {team_name:<12} vs {scenario_name:<8} | {result_shift:<13} | "
        f"省时 {time_delta:>5.1f}s | 触发 {prep_triggers:>3} | "
        f"余血差 {with_prep['player_hp_pct'] - no_prep['player_hp_pct']:>6.1f}% | "
        f"战备伤 {metric(with_prep, 'prep_damage') - metric(no_prep, 'prep_damage'):>7.1f} | "
        f"护盾差 {metric(with_prep, 'shield') - metric(no_prep, 'shield'):>7.1f} | "
        f"治疗差 {metric(with_prep, 'healing') - metric(no_prep, 'healing'):>7.1f} | "
        f"士气差 {metric(with_prep, 'morale') - metric(no_prep, 'morale'):>7.1f} | "
        f"流血差 {metric(with_prep, '流血') - metric(no_prep, '流血'):>7.1f} | "
        f"灼烧差 {metric(with_prep, '灼烧') - metric(no_prep, '灼烧'):>7.1f} | "
        f"反击差 {metric(with_prep, '反击') - metric(no_prep, '反击'):>7.1f}"
    )


def run_matrix(
    use_items: bool = True,
    team_filter: str | None = None,
    scenario_filter: str | None = None,
    diagnose: bool = False,
    print_header: bool = True,
) -> None:
    if print_header:
        print("三国斗阵 combat-sim v0.1")
        print("说明：临时抽象战斗沙盘，只用于角色定位、技能与装备方向验证。\n")
    for team_name, (hero_names, item_map) in TEAMS.items():
        if team_filter and team_filter not in team_name:
            continue
        for scenario_name, enemy_kinds in SCENARIOS.items():
            if scenario_filter and scenario_filter not in scenario_name:
                continue
            result = simulate(team_name, scenario_name, use_items=use_items)
            print(format_diagnosis(team_name, scenario_name, result) if diagnose else format_result(team_name, scenario_name, result))
        print()


def run_compare(team_filter: str | None = None, scenario_filter: str | None = None) -> None:
    print("三国斗阵 combat-sim v0.1 装备对照")
    print("说明：同一队伍同一试题分别跑无装备/有装备，观察装备是否放大对应流派。\n")
    for team_name in TEAMS:
        if team_filter and team_filter not in team_name:
            continue
        for scenario_name in SCENARIOS:
            if scenario_filter and scenario_filter not in scenario_name:
                continue
            with_items = simulate(team_name, scenario_name, use_items=True)
            no_items = simulate(team_name, scenario_name, use_items=False)
            print(format_compare(team_name, scenario_name, with_items, no_items))
        print()


def run_prep_compare(team_filter: str | None = None, scenario_filter: str | None = None, prep_filter: str | None = None) -> None:
    print("三国斗阵 combat-sim v0.1 战备对照")
    print("说明：同一队伍同一试题分别跑无战备/单个战备，观察高影响战备是否改变闭环。\n")
    for prep_name in PREPS:
        if prep_filter and prep_filter not in prep_name:
            continue
        for team_name in TEAMS:
            if team_filter and team_filter not in team_name:
                continue
            for scenario_name in SCENARIOS:
                if scenario_filter and scenario_filter not in scenario_name:
                    continue
                with_prep = simulate(team_name, scenario_name, use_items=True, preps=[prep_name])
                no_prep = simulate(team_name, scenario_name, use_items=True)
                print(format_prep_compare(team_name, scenario_name, prep_name, with_prep, no_prep))
            print()


def run_diagnosis(team_filter: str | None = None, scenario_filter: str | None = None, use_items: bool = True) -> None:
    print("三国斗阵 combat-sim v0.1 诊断模式")
    print("说明：用固定阈值把战斗结果翻译成策划可读的定位验证信号。\n")
    run_matrix(use_items=use_items, team_filter=team_filter, scenario_filter=scenario_filter, diagnose=True, print_header=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="三国斗阵设计验证用抽象战斗沙盘")
    parser.add_argument("--no-items", action="store_true", help="关闭装备，用于对照测试")
    parser.add_argument("--compare-items", action="store_true", help="输出装备开启/关闭的对照差值")
    parser.add_argument("--compare-preps", action="store_true", help="输出高影响战备开启/关闭的对照差值")
    parser.add_argument("--prep", default=None, help="只跑名称包含该文本的战备，例如：火势")
    parser.add_argument("--diagnose", action="store_true", help="输出角色定位诊断")
    parser.add_argument("--team", default=None, help="只跑名称包含该文本的队伍，例如：关羽")
    parser.add_argument("--scenario", default=None, help="只跑名称包含该文本的试题，例如：高甲")
    args = parser.parse_args()
    if args.compare_items:
        run_compare(team_filter=args.team, scenario_filter=args.scenario)
    elif args.compare_preps:
        run_prep_compare(team_filter=args.team, scenario_filter=args.scenario, prep_filter=args.prep)
    elif args.diagnose:
        run_diagnosis(team_filter=args.team, scenario_filter=args.scenario, use_items=not args.no_items)
    else:
        run_matrix(use_items=not args.no_items, team_filter=args.team, scenario_filter=args.scenario)

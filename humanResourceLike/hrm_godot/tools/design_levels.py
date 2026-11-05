# -*- coding: utf-8 -*-
"""设计 21-40 关：写程序 → 跑 free 模式得到真实输出 → 人工核对 → 写回 levels.json

为什么不手算 outbox：
手算八次有八次错，而且错了以后 Godot 那边的报错只会说「第 5 只应该是 7」，
不告诉你究竟是题错还是程序错。让程序自己吐出来，人只做「这输出对不对」的裁决。

一个反复吃到的坑，写在这里省得下次再踩：
**JUMPZ / JUMPN 不消耗手上的值。** 跳转过去时手还是满的，
所以每个「被跳转到」的标签，第一条几乎永远是 `MOVETO <废纸篓>`，
唯一的例外是这个标签本身就以要求手空的指令开头（COPYFROM / BUMPUP / INBOX）。
"""
import io
import json
import sys

sys.path.insert(0, "tools")
import vm_py  # noqa: E402

LV = []


def lv(**kw):
    LV.append(kw)


# ---------------------------------------------------------------- 组 A：流的形态
lv(id=21, name="Back to Front", cn="倒着点名",
   goal="牧羊人今晚倒着点名：先报 n，再一个个往下数到 1，最后报今晚一共数了几只。",
   inbox=[4], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPDN", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 0",
        "b:COPYFROM 0", "JUMPZ e", "OUTBOX",
        "COPYFROM 2", "ADD 0", "MOVETO 2",
        "BUMPDN 0", "MOVETO 3", "JUMP b",
        "e:MOVETO 3", "COPYFROM 2", "OUTBOX"],
   hint="这一轮要做两件事：把当前编号报出去，同时把它加进「今晚数了几个」里。",
   hint2="0 号格当倒数计数器，2 号格当累加器。JUMPZ 到出口时倒数已经用完，出口只剩一句「报总数」。")

lv(id=22, name="Pair Product", cn="成对相乘",
   goal="羊总是一对一对来的。把每对的乘积放进 OUTBOX。（2×3=6）",
   inbox=[2, 3, 4, 5], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "BUMPDN", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 0", "INBOX", "MOVETO 1",
        "b:COPYFROM 1", "JUMPZ c",
        "MOVETO 3", "BUMPDN 1", "MOVETO 3",
        "COPYFROM 2", "ADD 0", "MOVETO 2", "JUMP b",
        "c:MOVETO 3", "COPYFROM 2", "OUTBOX",
        "COPYFROM 2", "SUB 2", "MOVETO 2", "JUMP a"],
   hint="没有乘法牌，乘就是「加若干次」。第二只羊的编号就是加的次数。",
   hint2="0 号格放被乘数，1 号格放次数，2 号格攒结果。每加一次让 1 号格减一，减到 0 就输出。")

lv(id=23, name="New Records", cn="破纪录的羊",
   goal="记下每一个打破纪录的编号。数据以 0 结尾，只输出比之前所有都大的那些。",
   inbox=[3, 1, 5, 2, 9, 0], mem_size=3, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "JUMP", "JUMPZ", "JUMPN"],
   ref=["a:INBOX", "MOVETO 1",
        "COPYFROM 1", "JUMPZ c", "SUB 0", "JUMPN b",
        "MOVETO 2",
        "COPYFROM 1", "MOVETO 0",
        "COPYFROM 1", "OUTBOX", "JUMP a",
        "b:MOVETO 2", "JUMP a",
        "c:MOVETO 2"],
   hint="减法在这里不是算术，是比较：v 减去当前纪录，负的就说明没破纪录。",
   hint2="0 号格存当前纪录。判负就跳到「什么也不做」，但记得把手里的差值扔掉（写进废纸篓）。")

lv(id=24, name="Truckload", cn="每三只一车",
   goal="每数满 3 只就装一车，输出这一车的编号之和。（1+2+3=6）",
   inbox=[1, 2, 3, 4, 5, 6, 7, 8, 9], mem_size=5, mem_init=[0, 0, 0, 0, 3],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 2",
        "COPYFROM 1", "ADD 2", "MOVETO 1",
        "BUMPUP 0", "MOVETO 3",
        "COPYFROM 0", "SUB 4", "JUMPZ b", "MOVETO 3", "JUMP a",
        "b:MOVETO 3", "COPYFROM 1", "OUTBOX",
        "COPYFROM 4", "SUB 4", "MOVETO 1",
        "COPYFROM 4", "SUB 4", "MOVETO 0", "JUMP a"],
   hint="装车之后车要清空、计数要归零。木牌上没有「清零」牌，用「减自己」得到 0。",
   hint2="4 号格放着常量 3。计数到 3 就输出累加器，然后把 1 号格和 0 号格都清成 0。")

lv(id=25, name="Biggest of Three", cn="一车里最大的一只",
   goal="每三只一车，只输出这一车里最大的编号。",
   inbox=[1, 5, 3, 2, 8, 4, 9, 1, 2], mem_size=5, mem_init=[0, 0, 0, 0, 3], scratch=3,
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "BUMPUP", "JUMP", "JUMPZ", "JUMPN"],
   ref=[
        "a:INBOX", "MOVETO 2",
        "COPYFROM 2", "SUB 1", "JUMPN b",
        "COPYFROM 2", "MOVETO 1", "JUMP c",
        "b:MOVETO 3",
        "c:BUMPUP 0", "MOVETO 3",
        "COPYFROM 0", "SUB 4", "JUMPZ d", "MOVETO 3", "JUMP a",
        "d:MOVETO 3", "COPYFROM 1", "OUTBOX",
        "COPYFROM 4", "SUB 4", "MOVETO 1",
        "COPYFROM 4", "SUB 4", "MOVETO 0", "JUMP a"],
   hint="装车的方式和「每三只一车」一模一样，只是车里不留和、留最大。",
   hint2="每读一只先和 1 号格里当前的冠军比，比它大就换人。满 3 只输出冠军再清空。")

# ---------------------------------------------------------------- 组 B：哨兵与汇总
lv(id=26, name="Count and Sum", cn="数完再报个数",
   goal="读到 0 就收工。先报总和，再报一共数了几只。",
   inbox=[4, 7, 2, 0], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPUP", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 2",
        "COPYFROM 2", "JUMPZ c",
        "MOVETO 3",
        "COPYFROM 0", "ADD 2", "MOVETO 0",
        "BUMPUP 1", "MOVETO 3", "JUMP a",
        "c:MOVETO 3", "COPYFROM 0", "OUTBOX",
        "COPYFROM 1", "OUTBOX"],
   hint="0 是收工信号，不参与统计。收工之后才输出两份汇总。",
   hint2="0 号格攒和、1 号格攒个数。读进 2 号格后用 JUMPZ 判它是不是收工信号。")

lv(id=27, name="High and Low", cn="最高的和最低的",
   goal="读到 0 就收工。报出这群羊里最高的编号，再报最低的。",
   inbox=[4, 7, 2, 9, 1, 0], mem_size=5, mem_init=[0, 0, -99, 0, 99],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "JUMP", "JUMPZ", "JUMPN"],
   ref=[
        "a:INBOX", "MOVETO 3",
        "COPYFROM 3", "JUMPZ d", "SUB 1", "JUMPN b1",
        "COPYFROM 3", "MOVETO 1", "JUMP c1",
        "b1:MOVETO 2",
        "c1:COPYFROM 4", "SUB 3", "JUMPN c2",
        "COPYFROM 3", "MOVETO 4", "JUMP c3",
        "c2:MOVETO 2",
        "c3:JUMP a",
        "d:MOVETO 2", "COPYFROM 1", "OUTBOX", "COPYFROM 4", "OUTBOX"],
   hint="3 号格放当前读到的值，两把尺子各比一次：一次比高、一次比低。",
   hint2="2 号格是废纸篓。0 号格给了 -99、4 号格给了 99 当初始值，所以第一个数一定同时刷新两项纪录。")

lv(id=28, name="Doubling Nights", cn="每晚翻一倍",
   goal="输出 2 的 0 次方一直到 2 的 n 次方。n=4 就是 1,2,4,8,16。",
   inbox=[4], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPUP", "SUB", "JUMP", "JUMPZ"],
   ref=[
        "a:INBOX", "MOVETO 0",
        "BUMPUP 1", "OUTBOX",
        "b:COPYFROM 1", "ADD 1", "MOVETO 1",
        "COPYFROM 1", "OUTBOX",
        "BUMPUP 2", "MOVETO 3",
        "COPYFROM 0", "SUB 2", "JUMPZ c", "MOVETO 3", "JUMP b",
        "c:MOVETO 3"],
   hint="翻倍不需要乘法牌：自己加自己就是乘 2。",
   hint2="1 号格是当前值，2 号格数翻了几次。翻够 n 次就停。")

lv(id=29, name="Triangular Stack", cn="堆成三角",
   goal="前 n 个三角数：1，1+2，1+2+3…… n=4 输出 1,3,6,10。",
   inbox=[4], mem_size=5, mem_init=[], scratch=4,
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPUP", "SUB", "JUMP", "JUMPZ"],
   ref=[
        "a:INBOX", "MOVETO 0",
        "b:BUMPUP 1", "ADD 2", "MOVETO 2",
        "COPYFROM 2", "OUTBOX",
        "BUMPUP 3", "MOVETO 4",
        "COPYFROM 0", "SUB 3", "JUMPZ c", "MOVETO 4", "JUMP b",
        "c:MOVETO 4"],
   hint="每往上一层就多铺一行，铺满 n 层为止。",
   hint2="1 号格是这一层的层号，2 号格是累加到现在的总数。先加层号、再输出、再比层数。")

lv(id=30, name="Square Dance", cn="平方牧场",
   goal="输出 1 到 n 的平方和。n=4 就是 1+4+9+16=30。",
   inbox=[4], mem_size=7, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPUP", "BUMPDN", "SUB", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 0",
        "b:BUMPUP 1", "MOVETO 6",
        "COPYFROM 3", "SUB 3", "MOVETO 3",
        "COPYFROM 1", "MOVETO 4",
        "c:COPYFROM 4", "JUMPZ d", "MOVETO 6", "BUMPDN 4", "MOVETO 6",
        "COPYFROM 3", "ADD 1", "MOVETO 3", "JUMP c",
        "d:MOVETO 6", "COPYFROM 3", "ADD 2", "MOVETO 2",
        "BUMPUP 5", "MOVETO 6",
        "COPYFROM 0", "SUB 5", "JUMPZ e", "MOVETO 6", "JUMP b",
        "e:MOVETO 6", "COPYFROM 2", "OUTBOX"],
   hint="平方就是 k 个 k 相加。所以这关是「循环里面再套一个加 k 次的循环」。",
   hint2="1 号格是 k，3 号格装 k×k，2 号格攒总和。内层数满 k 次就出来把 3 号格加进总和。")

# ---------------------------------------------------------------- 组 C：多状态
lv(id=31, name="Two Sheep Back", cn="往前看两只",
   goal="斐波那契：1,1,2,3,5,8…… 输出前 n 项。",
   inbox=[6], mem_size=6, mem_init=[], scratch=5,
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPUP", "SUB", "JUMP", "JUMPZ"],
   ref=[
        "a:INBOX", "MOVETO 0",
        "BUMPUP 1", "OUTBOX",
        "BUMPUP 4", "MOVETO 4",
        "BUMPUP 3", "OUTBOX",
        "BUMPUP 4", "MOVETO 4",
        "b:COPYFROM 1", "ADD 3", "MOVETO 2",
        "COPYFROM 3", "MOVETO 1",
        "COPYFROM 2", "MOVETO 3",
        "COPYFROM 3", "OUTBOX",
        "BUMPUP 4", "MOVETO 4",
        "COPYFROM 0", "SUB 4", "JUMPZ c", "MOVETO 5", "JUMP b",
        "c:MOVETO 5"],
   hint="斐波那契要记住两个数，而手上只抱得动一个 —— 两个数各占一格木牌。",
   hint2="1 号和 3 号格是相邻的两项。每次先把它们加起来放到 2 号格，再整体往前挪一格，最后才输出。")

lv(id=32, name="Squash Duplicates", cn="连着的只留一只",
   goal="连续重复的编号只输出第一次。1,1,2,2,3,1,1 → 1,2,3,1",
   inbox=[1, 1, 2, 2, 3, 1, 1], mem_size=4, mem_init=[-999, 0, 0, 0],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 1",
        "COPYFROM 1", "SUB 0", "JUMPZ b",
        "MOVETO 2",
        "COPYFROM 1", "MOVETO 0",
        "COPYFROM 1", "OUTBOX", "JUMP a",
        "b:MOVETO 2", "JUMP a"],
   hint="要判断「和上一只一样吗」，就得把上一只记下来。",
   hint2="0 号格存上一只，初始给了 -999 保证第一只一定算新的。相等就扔掉，不等就输出并更新。")

lv(id=33, name="Factorial Night", cn="阶乘的夜班",
   goal="输出 n 的阶乘。5! = 1×2×3×4×5 = 120。",
   inbox=[5], mem_size=7, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "BUMPUP", "BUMPDN", "SUB", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 0",
        "BUMPUP 1", "MOVETO 6",
        "BUMPUP 2", "MOVETO 6",
        "b:COPYFROM 3", "SUB 3", "MOVETO 3",
        "COPYFROM 1", "MOVETO 4",
        "c:COPYFROM 4", "JUMPZ d", "MOVETO 6", "BUMPDN 4", "MOVETO 6",
        "COPYFROM 3", "ADD 2", "MOVETO 3", "JUMP c",
        "d:MOVETO 6", "COPYFROM 3", "MOVETO 2",
        "COPYFROM 1", "SUB 0", "JUMPZ e",
        "MOVETO 6", "BUMPUP 1", "MOVETO 6", "JUMP b",
        "e:MOVETO 6", "COPYFROM 2", "OUTBOX"],
   hint="阶乘不是加法题，是「乘法套在循环里」：每轮的结果要乘上当前的 i。",
   hint2="2 号格是累乘结果（从 1 开始），1 号格是当前的 i。内层用 3 号格一次次加自己，加满 i 次就是乘 i。")

lv(id=34, name="Common Den", cn="挤一个窝",
   goal="输入两个数，输出它们的最大公约数。（12 和 18 → 6）",
   inbox=[12, 18], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "JUMP", "JUMPZ", "JUMPN"],
   ref=["a:INBOX", "MOVETO 0", "INBOX", "MOVETO 1",
        "b:COPYFROM 0", "SUB 1", "JUMPZ e", "JUMPN c",
        "MOVETO 2", "COPYFROM 0", "SUB 1", "MOVETO 0", "JUMP b",
        "c:MOVETO 2", "COPYFROM 1", "SUB 0", "MOVETO 1", "JUMP b",
        "e:MOVETO 2", "COPYFROM 0", "OUTBOX"],
   hint="欧几里得的办法：大数减小数，一直减到两个数相等为止。",
   hint2="0 号和 1 号格各放一个数。每轮用减法判谁大，把大的那格削掉一份。相等时输出任意一个。")

lv(id=35, name="Plus Minus", cn="一加一减",
   goal="隔一只加、隔一只减：5-4+3-2+1。读到 0 收工，输出结果。",
   inbox=[5, 4, 3, 2, 1, 0], mem_size=4, mem_init=[0, 0, 0, 1],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 1",
        "COPYFROM 1", "JUMPZ e",
        "MOVETO 2",
        "COPYFROM 3", "JUMPZ m",
        "MOVETO 2",
        "COPYFROM 0", "ADD 1", "MOVETO 0",
        "COPYFROM 3", "SUB 3", "MOVETO 3", "JUMP a",
        "m:MOVETO 2", "COPYFROM 0", "SUB 1", "MOVETO 0",
        "BUMPUP 3", "MOVETO 2", "JUMP a",
        "e:MOVETO 2", "COPYFROM 0", "OUTBOX"],
   hint="要在两件事之间来回切，就得有一格记住「这一轮该加还是该减」。",
   hint2="3 号格当开关：1 表示加、0 表示减。每轮结束把它翻一次（减自己或加一都行）。")

# ---------------------------------------------------------------- 组 D：真章
lv(id=36, name="Sort Two", cn="大的站前面",
   goal="每两只一组，按大到小输出。（5,3 → 5,3；2,7 → 7,2）",
   inbox=[5, 3, 2, 7, 4, 4], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "JUMP", "JUMPN"],
   ref=["a:INBOX", "MOVETO 0", "INBOX", "MOVETO 1",
        "COPYFROM 0", "SUB 1", "JUMPN b",
        "MOVETO 2",
        "COPYFROM 0", "OUTBOX", "COPYFROM 1", "OUTBOX", "JUMP a",
        "b:MOVETO 2", "COPYFROM 1", "OUTBOX", "COPYFROM 0", "OUTBOX", "JUMP a"],
   hint="先比大小，再决定先把谁推出去。两条分支各输出两个，只是顺序不同。",
   hint2="0 号格放第一只、1 号格放第二只。用差值的正负选分支。")

lv(id=37, name="Climb Check", cn="今晚有没有掉队",
   goal="读到 0 收工。报出一共出现过几次「比上一只小」。",
   inbox=[3, 5, 4, 8, 2, 0], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "SUB", "BUMPUP", "JUMP", "JUMPZ", "JUMPN"],
   ref=["a:INBOX", "MOVETO 1",
        "COPYFROM 1", "JUMPZ e", "SUB 0", "JUMPN b",
        "MOVETO 3",
        "COPYFROM 1", "MOVETO 0", "JUMP a",
        "b:MOVETO 3", "BUMPUP 2", "MOVETO 3",
        "COPYFROM 1", "MOVETO 0", "JUMP a",
        "e:MOVETO 3", "COPYFROM 2", "OUTBOX"],
   hint="「比上一只小」就是这一只减上一只为负。掉的次数记在一格木牌里。",
   hint2="0 号格存上一只，2 号格数掉队次数。判负之后别忘了把这一只也记成「上一只」。")

lv(id=38, name="Two Pens", cn="两个圈",
   goal="用 0 把羊群分成两拨，每遇到一个 0 就报出这一拨的总和。（1,2,0,3,4,5,0 → 3、12）",
   inbox=[1, 2, 0, 3, 4, 5, 0], mem_size=3, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "JUMP", "JUMPZ"],
   ref=["a:INBOX", "MOVETO 1",
        "COPYFROM 1", "JUMPZ b",
        "MOVETO 2",
        "COPYFROM 0", "ADD 1", "MOVETO 0", "JUMP a",
        "b:MOVETO 2", "COPYFROM 0", "OUTBOX",
        "COPYFROM 2", "SUB 2", "MOVETO 0", "JUMP a"],
   hint="0 既当分隔符，也当收工信号 —— 每遇到一个就报一拨，然后把累加器清空。",
   hint2="2 号格是废纸篓，用来把累加器减成 0。清空之后继续读，数据读完自然就收工。")

lv(id=39, name="Peak Prefix", cn="最高的那道坎",
   goal="一路累加，读到 0 收工，报出累加过程中曾经到过的最大值。（负数会把累加拉下来）",
   inbox=[3, -1, 4, -5, 2, -3, 0], mem_size=4, mem_init=[],
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "JUMP", "JUMPZ", "JUMPN"],
   ref=[
        "a:INBOX", "MOVETO 1",
        "COPYFROM 1", "JUMPZ e",
        "MOVETO 3",
        "COPYFROM 0", "ADD 1", "MOVETO 0",
        "COPYFROM 0", "SUB 2", "JUMPN b",
        "MOVETO 3",
        "COPYFROM 0", "MOVETO 2", "JUMP c",
        "b:MOVETO 3",
        "c:JUMP a",
        "e:MOVETO 3", "COPYFROM 2", "OUTBOX"],
   hint="累加器一直在变，但「历史最高」只在新值更高时才更新。",
   hint2="0 号格是累加器，2 号格是历史最高。每轮加完就比一次，正数才更新。")

lv(id=40, name="The Whole Night", cn="一整夜",
   goal="最后一关。读到 0 收工，依次报出：总和、一共几只、最低的编号、最高的编号。四样都要。",
   inbox=[6, 3, 8, 2, 7, 0], mem_size=7, mem_init=[0, 0, 0, 0, 99, 0, -99], scratch=5,
   allowed=["INBOX", "OUTBOX", "COPYFROM", "MOVETO", "ADD", "SUB", "BUMPUP", "JUMP", "JUMPZ", "JUMPN"],
   ref=[
        "a:INBOX", "MOVETO 1",
        "COPYFROM 1", "JUMPZ e",
        "MOVETO 3",
        "COPYFROM 0", "ADD 1", "MOVETO 0",
        "BUMPUP 2", "MOVETO 3",
        "COPYFROM 4", "SUB 1", "JUMPN b",
        "MOVETO 3",
        "COPYFROM 1", "MOVETO 4", "JUMP c",
        "b:MOVETO 3",
        "c:COPYFROM 1", "SUB 6", "JUMPN d",
        "MOVETO 3",
        "COPYFROM 1", "MOVETO 6", "JUMP f",
        "d:MOVETO 3",
        "f:JUMP a",
        "e:MOVETO 5", "COPYFROM 0", "OUTBOX",
        "COPYFROM 2", "OUTBOX", "COPYFROM 4", "OUTBOX",
        "COPYFROM 6", "OUTBOX"],
   hint="这一关是全篇的收尾：一个累加器、一个计数器、两把尺子（最低和最高），四样同时在跑。",
   hint2="0 号格和、2 号格个数、4 号格最低（初始 99）、6 号格最高（初始 -99）。收工后按「和 / 个数 / 最低 / 最高」输出。")


def _repair(d):
    """自动补「清手」。

    JUMPZ / JUMPN 不消耗手上的值 —— 跳过去时手还是满的，于是目标标签的第一句
    经常就是「COPYFROM 要求手空」。这类错误有二十处，靠手改一定漏，
    所以让失败信息自己指路：在失败那一句前面插一条 MOVETO <废纸篓>，
    直到跑通为止。插入的多余行不影响语义（废纸篓里的值没人读）。
    """
    ref = list(d["ref"])
    scratch = int(d.get("scratch", min(5, int(d.get("mem_size", 8)) - 1)))
    for _ in range(80):
        vm = vm_py.VM(d, ref, free=True)
        if vm.run():
            break
        if "要求手空" not in vm.msg:
            break
        at = vm.pc - 1
        if not (0 <= at < len(ref)):
            break
        line = ref[at]
        if ":" in line:
            lab, rest = line.split(":", 1)
            ref[at:at + 1] = ["%s:MOVETO %d" % (lab, scratch), rest]
        else:
            ref.insert(at, "MOVETO %d" % scratch)
    return ref


def main():
    out = []
    for d in LV:
        d["ref"] = _repair(d)
        vm = vm_py.VM(d, d["ref"], free=True)
        ok = vm.run()
        tag = "#%d %-20s" % (d["id"], d["name"])
        if not ok:
            print("FAIL %s：%s（out=%s）" % (tag, vm.msg, vm.outbox))
            continue
        print("%s size=%-3d out=%s" % (tag, vm_py.program_size(vm.prog), vm.outbox))
        if "--dump" in sys.argv:
            for k, line in enumerate(d["ref"]):
                print("      %2d| %s" % (k + 1, line))
        row = dict(d)
        row["outbox"] = vm.outbox
        out.append(row)

    if "--sort" in sys.argv:
        # 21 关往后按「纯解题分」重排：这一段的设计顺序原本是
        # 「引入 → 练习 → 挑战」，每组的引入关天然比上一组的挑战关轻，
        # 曲线就成了锯齿。既然这 20 关还没有人打过（没有存档依赖），
        # 直接按分排序最省事 —— 难度这才真的单调往上走。
        for r in out:
            r["_sc"] = vm_py.score_plain(
                r, vm_py.parse(r["ref"]))
        out.sort(key=lambda r: r["_sc"])
        for i, r in enumerate(out):
            r["id"] = 21 + i
        print("\n=== 排序后 ===")
        for r in out:
            print("  #%02d %-20s %.1f" % (r["id"], r["name"], r["_sc"]))

    if len(out) != len(LV):
        print("\n有 %d 关没跑通，先别写盘。" % (len(LV) - len(out)))
        return 1

    if "--write" in sys.argv:
        path = "data/levels.json"
        levels = json.load(io.open(path, encoding="utf-8"))
        levels = [l for l in levels if int(l["id"]) <= 20]
        order = ["id", "name", "cn", "goal", "inbox", "outbox", "allowed",
                 "mem_size", "mem_init", "ref", "hint", "hint2"]
        lists = ("inbox", "outbox", "allowed", "mem_init", "ref")
        for r in out:
            levels.append({k: (r.get(k, []) if k in lists else r.get(k)) for k in order})
        io.open(path, "w", encoding="utf-8", newline="\n").write(
            json.dumps(levels, ensure_ascii=False, indent=1) + "\n")
        print("\n已写入 %s：%d 关" % (path, len(levels)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

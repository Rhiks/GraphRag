"""
测试脚本：测试 recognize_xishuashua 功能

使用方法：
1. 确保已配置好环境变量或 .env 文件（包含 API Key）
2. 准备一张学生作答的图片文件
3. 运行脚本：python test_xishuashua.py
"""

import json

# 导入喜刷刷功能
from _openai.xishuashua_ocr import recognize_xishuashua_async

# 用户提供的题干
USER_STEM_base = """1. I don't mind a small ________.
2. Let's work ________ the problem together.
3. It's good to ________ ________ ________.

4. Give a helping ________.
5. It's okay to ________ ________.
6. It's okay to ________ mistakes.
7. Let's work out the problem ________.
8. Let's ________ out the problem together.
9. It's good to ________ your life.
10. I ________ ________ papers.
"""
img_url_base = "https://pic1.imgdb.cn/item/69bb5c5ab96fa53fd04cd60d.jpg"

img_url_0 = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1775121507925_0_9459214.1775121507892.jpg";
USER_STEM_0 = """1.________ you tomorrow!
2.See ________ tomorrow!
3.See you ________!
4.Bye! ________ ________ ________!
5.________ you, please.
6.________ ________, please.
7.I can put English ________ use.
8.I ________ the desk with care.
9.I can put ________ into use.
10.I can ________ ________ ________ ________."""

img_url_1 = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1775122256024_1_9459214.1775122256008.jpg"

USER_STEM_1 = """"Sam: Lucas, what do you do (1) ________ you get up?
Lucas: I brush my teeth. Then I go (2) ________ the classroom.
Sam: We can (3) ________ our English books there.
Lucas: (4) ________ ________!
Sam: Thanks! By the way, let's play together tomorrow.
Lucas: Great! (5) ________ ________ ________!"""


img_url_2 = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1775127442545_1_9459214.1775127442530.jpg"
USER_STEM_2 = """
Sam: Lucas, it's 7 o'clock. It's time to (1) __________ __________!
Lucas: OK. I need to (2) __________ my hands first.
Sam: Don't forget to wash your (3) __________ too!
Lucas: Yes! And I will brush my (4) __________ after that.
Sam: Then we can (5) __________ quickly. We don't want to be late!"""


img_url_t0  = "https://cdn.phototourl.com/free/2026-04-05-1b6f7037-2b16-4b1e-8040-4d263c6d4dd7.jpg"
USER_STEM_t0  = """
1. 句子填空
The pink flowers in our school garden look so __________.
我们学校花园里的粉色花朵看起来真可爱。
2. My deskmate shares her interesting __________ book with me every afternoon.
我的同桌每天下午都和我分享她有趣的英语书。
3. Don’t worry about the light rain—it’s _________ _________ ________ _________!
别担心这场小雨，真是适合鸭子的好天气呀！
4. Could you tell me what the phrase “helpful” __________ in this English dialogue?
你能告诉我英语对话里“helpful”这个短语是什么意思吗？
5. There’s a Chinese __________ about “plants grow with care” in our textbook.
我们课本里有一句“精心照料，植物才茂”的中国谚语。
6. __________ __________ the phrase “feel free” __________?
“feel free”这个短语是什么意思？
7. The note on the desk is blue. ________ ________ “Please return the book on time”.
课桌上的便签是蓝色的，它的意思是“请按时还书”。
8. _________ _________ _________ _________ _________ of using the phrase
“look around”?
你能举一个使用“look around”这个短语的例子吗？
9. When I have trouble with English, my friend always wants to __________ me a
hand.
当我英语遇到困难时，我的朋友总是想帮我一把。
10. Let’s ask the teacher about the __________ before visiting the school garden.
去参观学校花园之前，我们问问老师天气怎么样吧。"""

img_url_t1 ="https://cdn.phototourl.com/free/2026-04-05-6ea96d3a-c6ae-4cb0-91d8-14fafd998cd4.jpg"
USER_STEM_t1 = """
Alice: The school garden has (1) __________
flowers!
Sam: Yes! We learn many (2) __________
sayings in class.
Alice: It’s drizzling—what (3) __________
__________ __________ __________!
Sam: Cool! Do you know what that animal
saying (4) __________?
Alice: A funny (5) __________ says it means
mild rain is nice for ducks!
篇章填空 1
爱丽丝：学校花园里有可爱的花！
山姆：是啊！我们在课堂上学了很
多英语谚语。
爱丽丝：正在下毛毛雨——真是适
合鸭子的好天气呀！
山姆：好酷！你知道那个动物谚语
是什么意思吗？
爱丽丝：一句有趣的谚语说，它指
小雨对鸭子来说很舒服！
"""
img_url_t2 = "https://cdn.phototourl.com/free/2026-04-05-6ea96d3a-c6ae-4cb0-91d8-14fafd998cd4.jpg"
USER_STEM_t2 = """
Alice: (1) __________ __________ "windy"
__________?
Sam: (2) __________ __________ it’s a day
with wind.
Alice: (3) __________ __________
__________ __________ __________?
Sam: Sure! I can (4) __________ you one:
"The bamboo bends on a windy day."
Alice: Oh right! What’s the (5) __________
like today? Is it windy?
篇章填空 2
爱丽丝：“有风的”是什么意思？
山姆：它的意思是有风的一天。
爱丽丝：你能举个例子吗？
山姆：当然！我可以给你一个：
“有风的日子里，竹子会弯曲。”
爱丽丝：哦对！今天天气怎么
样？有风吗？"""
img_url_t3 = "https://cdn.phototourl.com/free/2026-04-05-6b959ed4-a69f-4ef0-be2d-048eb0aaad81.jpg"
USER_STEM_t3 = """
1. Your English reading is improving so fast—
__________ __________
__________!
你的英语阅读进步真快——继续加油呀！
2. Tom studies every evening and never gives up; he’s a __________ student.
汤姆每晚都学习，从不放弃，他是个勤奋的学生。
3. The story says we shouldn’t __________ pearls before people who don’t cherish
them.
故事里说，我们不该把珍珠丢给不珍惜它们的人。
4. Please hand in your homework __________ the English class starts tomorrow.
明天英语课开始前，请把作业交上来。
5. Our teacher often shares funny __________ __________ that come from animals.
我们老师经常分享源自动物的有趣英语谚语。
6. My grandma has a ring with a shiny __________ that she likes very much.
奶奶有一枚带闪亮珍珠的戒指，她非常喜欢。
7. To make our garden beautiful, we need to __________ the flowers watered
regularly.
要让我们的花园漂亮，我们得定期给花浇水，保持湿润。
8. We had a __________ time picking fresh carrots in the school garden last week.
上周我们在学校花园摘新鲜胡萝卜，玩得超开心！
9. Helping the teacher tidy the bookshelf is a small but important __________ for
me.
帮老师整理书架对我来说是件小但重要的事。
"""
img_url_t4 = "https://cdn.phototourl.com/free/2026-04-05-9ff21014-fdd2-417e-b382-d6ce253f5672.jpg"
USER_STEM_t4 = """
Alice: Many (1) __________ __________
come from animals.
Sam: Like "busy as a bee"? It means someone
is (2) __________, right?
Alice: Yes! If you keep studying, I’ll say " (1)
__________ __________ __________!".
Sam: What’s "to (3) __________ pearls (4)
__________ swine" mean?
Alice: It’s the English for "对牛弹琴"!
篇章填空 1
爱丽丝：很多英语谚语源自动物。
山姆：比如“像蜜蜂一样忙碌”？它
指某人很勤奋，对吗？
爱丽丝：是的！如果你坚持学习，
我会说“继续加油！”
。
山姆：“对牛弹琴” （字面意为“把珍
珠丢在猪面前”）是什么意思？
爱丽丝：它就是“对牛弹琴”的英文
表达呀！
"""
img_url_t5 = "https://cdn.phototourl.com/free/2026-04-05-9ff21014-fdd2-417e-b382-d6ce253f5672.jpg"
USER_STEM_t5 = """
Alice: You helped tidy the garden! (1)
__________ __________! (2) __________
it up next time!
Sam: Thanks! Do you know the saying "cast
(3) __________ before swine"?
Alice: Yes! You did a (4) __________ job
explaining it.
Sam: I’ll keep doing my (5) __________
well!
篇章填空 2
爱丽丝：你帮忙整理了花园！做
得好！下次继续保持呀！
山姆：谢谢！你知道“对牛弹
琴”（字面意为“把珍珠丢在猪面
前”）这个谚语吗？
爱丽丝：知道！你解释得真不
错。
山姆：我会坚持把我的工作做好
的！"""
img_url_t6 = "https://cdn.phototourl.com/free/2026-04-05-61163945-058e-4a78-9351-267fd23cb522.jpg"
USER_STEM_t6 = """1. You can
_____________ your fingers after writing down the colour names.
写下颜色名称后，你可以给你的手指涂色。
2. First colour Q, A, and Z
先把 Q、A 和 Z 涂成蓝色。
.
_______________
3. I use a
____________ _____________
我用一支彩色铅笔画了一只漂亮的小鸟。
to draw a beautiful little bird.
4.
"Bai" is my last name. It means "
_____________
我姓“白”
，在中文里它的意思是“白色”
。
" in Chinese.
5. My ____________
is yellow, just like the colour of bananas.
我的铅笔是黄色的，就像香蕉的颜色。
6. What
_____________ you see? Circle them.
你看到了什么？把它们圈出来。
7.
—First colour Q, A, and Z blue.
—
—先把 Q、A 和 Z 涂成蓝色。
_________
. I will colour W, S, and X green.
—好的。我会把 W、S 和 X 涂成绿色。
8. How do you
tofu? It is T-O-F-U.
___________
你怎样拼写豆腐这个单词？它是 T-O-F-U。
9.
_______
many colours do you know? Can you type them on a keyboard?
你认识多少种颜色？你能在键盘上把它们打出来吗？
10.
blue? - It's B-L-U-E.
_______ ________ _________ _________
蓝色怎么拼写？—它是 B-L-U-E。"""
img_url_t7 = "https://cdn.phototourl.com/free/2026-04-05-454881a9-cdb7-4961-8722-694e88053786.jpg"
USER_STEM_t7 = """A: I have a (1)________ pen and a (2)____
book.
B: (3)_____________________
blue?
A: It's B-L-U-E.
B: I have some (4) _______________
. Let's
draw a cat!
A: (5) _____
! Let's start now!
A: 我有一支蓝色的钢笔和一本白色的书。
B: 蓝色怎么拼写呀？
A: 是 B-L-U-E。
B: 我有一些彩色铅笔。我们来画一只小猫
吧！
A: 好的！我们现在就开始吧！
篇章填空 2
A: Hello! (1)____
do you (2)____ your
homework?
B: First, I use my (3)____
. Then, I read the
questions carefully.
A: Look! I have a new (4)____ pencil. It's pink.
B: Cool! How do you (5)____
"pink"?
A: It's P-I-N-K.
A：你好！你是怎么做作业的呀？
B：首先，我会用上我的铅笔。然后，我会
认真读题目。
A：看！我有一支新的彩色铅笔，是粉色的
哦。
B：好酷呀！你怎么拼写“pink”这个词呀？
A：是 P-I-N-K 哦。
"""
img_url_t7 = "https://cdn.phototourl.com/free/2026-04-05-b6c5e06e-b8d0-429c-81d7-e5ec01652b95.jpg"
USER_STEM_t7 = """
1. I'm Sam. Nice to
__________you!
我是山姆，很高兴认识你！
2.
, Sam. I'm Mr. Lee.
__________________________
很高兴认识你，山姆，我是李老师。
3. Good morning!
_______________________________
早上好！你叫什么名字？
?
4.
May Stone.
__________ __________ __________
我叫 May Stone。
5.
Aiwen.
____________
我是艾文。
6. Where's
__________
你的书包在哪？
bag?
7. Apples are
_______________
苹果是红色的。
.
8. Bananas are
香蕉是黄色的。
.
______________
9. This is
这是我的钢笔。
__________ pen.
10. I will colour trees
我把树涂成绿色。
.
____________
"""
img_url_t8 = "https://cdn.phototourl.com/free/2026-04-05-bcf09ac8-02e7-4324-b241-78f7e48245d7.jpg"
USER_STEM_t8 = """
A: Good morning! (1)______________________
?
B: Good morning! (2)________________
Yiming.
A: Nice to meet you, Yiming! Look at my pen. It's
(3)__________
.
B: Wow, it's cool! What's (4)________
name?
A: Oh, (5)_________
Sam. Nice to meet you!
A：早上好！你叫什么名字？
B：早上好！我的名字是一鸣。
A：很高兴认识你，
一鸣！看我的钢笔，
它是黄色的。
B：哇，好酷呀！你叫什么名字？
A：哦，我是山姆。很高兴认识你！
篇章填空 2
A: Hello! I'm May. What's your name?
B: Hi! (1)____
name is Tom. Nice to (2)____ you!
A: (3) ________________
, too! Look at the
apples. They are (4)_______
.
B: And look at the trees. They are (5)________
.
A: Wow, they are so nice!
A：你好！我是梅。你叫什么名字？
B：你好！我的名字是汤姆。很高兴认识
你！
A： 我也很高兴认识你！ 看这些苹果， 它
们是红色的。
B：再看这些树，它们是绿色的。
A：哇，它们真好看！"""
img_url_t9 = "https://cdn.phototourl.com/free/2026-04-05-1a2f0f6c-01b4-4e53-a135-a26a7132fa2d.jpg"
USER_STEM_t9 = """1. I ________ ________ to my friends.
我认真听我的朋友们说话。
2. Say ________ words.
说好听的话。
3. I listen to my friends ________.
我认真地听我的朋友们说话。
4. ________ ________ your things.
把你的东西收拾好。
5. Can you ________ me with my book?
你能帮我拿一下书吗？
6. I ________ to my friends carefully.
我认真地听我的朋友们说话。
7. ________ a helping hand.
伸出援助之手。
8. This is a nice ________.
这是一个好听的词。
9. ________ ________ ________.
说好听的话。
10. ________ ________ ________ ________.
伸出援助之手。"""
img_url_t10 = "https://cdn.phototourl.com/free/2026-04-05-11ad1015-1f4f-4d78-928e-0970e996227a.png"
USER_STEM_t10="""
Mr Lee: Sam, please (1) __________
__________. We need to tidy the classroom.
Sam: OK, Mr Lee. I will (2) __________ my
classmates first.
Mr Lee: Good. You are so (3) __________ to
everyone.
Sam: I know. I can (4) __________
__________ the books (5) __________.
Mr Lee: Well done! Let's finish it together.
李老师：山姆，请认真听讲。我们
需要整理教室。
山姆：好的，李老师。我要先帮助
我的同学们。
李老师：很好。你对大家真是太友
善了。
山姆：我知道的。我会仔细地把书
本收拾好。
李老师：做得好！我们一起把它完
成吧。
篇章填空 2
Mr Lee: Class, please (1) ________ carefully.
Today we’ll talk about good classroom
manners.
Student A: We should (2) __________
__________ __________ to each other, right?
Mr Lee: Exactly! And a kind (3) ________ can
make everyone happy.
Student B: What else should we do?
Mr Lee: We should (4) ________ others a hand
when they are in trouble.
Student A: Oh, that’s (5) __________
__________ __________ __________! It’s on
our classroom rules list.
李老师：同学们，请认真听讲。今
天我们来聊聊课堂上的文明行为
规范。
学生甲：我们应该对彼此说友善
的话，对吗？
李老师：完全正确！一句友善的话
语能让大家都开心。
学 生 乙 ： 我 们 还 应 该 做 些 什 么
呢？
李老师：当别人遇到困难时，我们
应该伸出援手。
学生甲：哦，那就是伸出援助之
手！这在我们的班规清单上呢。"""
img_url_t11 = "https://cdn.phototourl.com/free/2026-04-05-523cb72f-6ba4-4c55-b3e5-b8c9430815ec.png"
USER_STEM_t11 = """
1. Read and learn about ________ ________.
读一读并学习课堂规则。
2. You can try your ________ at school.
你可以在学校尽自己最大的努力。
3. This is a good classroom ________.
这是一条很好的课堂规则。
4. ________ nice words.
说好听的话。
5. Take turns to ________.
轮流说话。
6. This is ________ new school bag.
这是你的新书包。
7. ________ ________ ________.
尽你最大的努力。
8. ________ ________ to speak.
轮流说话。
9. Don't ________ in the classroom.
不要在教室里跑。
10. Don't run ________ the classroom.
不要在教室里跑。
"""
img_url_t12  = "https://cdn.phototourl.com/free/2026-04-05-21e9bba9-34d3-448f-9d1f-c1523dcba520.png"
USER_STEM_t12 = """Mr Lee: Boys and girls, let's talk about our (1)
__________ __________.
Student: My (2) __________ rule is "be
polite"!
Mr Lee: Good! We should (3) __________
nice words to each other.
Student: Yes! And we need to (4) __________
quietly in class.
Mr Lee: Exactly! Everyone must follow this
important (5) __________.
李老师：孩子们，我们来聊聊我们
的班规吧。
学生：我认为最好的班规是“讲礼
貌”！
李老师：很好！我们应该对彼此说
友善的话。
学生：是的！而且我们在课堂上需
要小声说话。
李老师：完全正确！个人都必须
遵守这条重要的规则。
篇章填空 2
Mr Lee: Boys and girls, let's talk about (1)
________ classroom rules.
Student A: We should (2) ________ ________
________ in class every day.
Mr Lee: Correct! And we must (3) ________
________ to speak politely.
Student B: What else should we remember?
Mr Lee: No one can (4) ________ (5)
________ the classroom. That's an important
rule!
李老师：孩子们，我们来聊聊你们
的班规吧。
学生甲：我们应该在课堂上全力
以赴。
李老师：没错！而且我们必须轮流
礼貌发言。
学 生 乙 ： 我 们 还 需 要 记 住 什 么
呢？
李老师：没有人可以在教室里奔
跑。这是一条很重要的规则！"""
img_url_t13 = "https://cdn.phototourl.com/free/2026-04-05-96e5239c-8833-46bd-a39f-372f42f30c5b.png"
USER_STEM_t13 = """
Dad: Sam, what do you (1) __________
__________ do this afternoon?
Sam: I (2) __________ __________
__________ to the school club.
Dad: Great! When do you read every day?
Sam: (3) __________ read __________ 7:00
__________ 8:00 after breakfast.
Dad: Don’t forget to take a bus (4) __________
the (5) __________ stop.
爸爸：山姆，今天下午你想做什
么？
山姆：我要坐公交车去学校俱乐
部。
爸爸：好极了！你天什么时候看
书呀？
山姆：我天早饭后从七点到八
点看书。
爸爸：别忘了去家附近的公交站
坐公交车哦。
篇章填空 2
Dad: Sam, what do you (1) __________ to do
(2) __________ day?
Sam: (3) __________ read books __________
7:00 p.m.
Dad: Do you read (4) __________ 7:00 to 8:00
every day?
Sam: (5) __________! But sometimes I play
sports first.
爸爸：山姆，你天想做什么？
山姆：我晚上七点看书。
爸爸：你是天从七点读到八点
吗？
山姆：也许吧！不过有时候我会先
做运动。
"""
img_url_t14 = "https://cdn.phototourl.com/free/2026-04-05-44997d21-8f98-44fb-8c43-ac247d65fe44.png"
USER_STEM_t14="""1. I ________ dinner at six fifty.
我在六点五十分吃晚餐。
2. I watch TV at eight ________.
我在八点二十分看电视。
3. I watch TV at ________ twenty.
我在八点二十分看电视。
4. I watch TV at ________ ________.
我在八点二十分看电视。
5. I watch TV at ________ forty.
我在七点四十分看电视。
6. I have dinner at ________ ________.
我在六点五十分吃晚餐。
7. I have dinner at ________ fifty.
我在六点五十分吃晚餐。
8. I watch TV at seven ________.
我在七点四十分看电视。
9. I watch TV at ________ ________.
我在七点四十分看电视。
10. I have dinner at six ________.
我在六点五十分吃晚餐。"""
img_url_t15 = "https://cdn.phototourl.com/free/2026-04-05-ca327658-12da-4543-b7a7-ceb6a66b3f4a.png"
USER_STEM_t15 ="""Dad: Sam, do you (1) __________ a new
timetable for your day?
Sam: Yes! My reading time is from seven (2)
__________ to (3) __________ o'clock.
Dad: Great! And when do you go to bed?
Sam: I go to bed at (4) __________
__________ every night.
Dad: Perfect! You need to get up at (5)
__________ o'clock tomorrow morning.
爸爸：山姆，你有一份新的日时
间表吗？
山姆：有呀！我的阅读时间是从七
点二十分到八点钟。
爸爸：太棒了！那你几点上床睡觉
呢？
山姆：我天晚上八点二十分上
床睡觉。
爸爸：很好！你明天早上需要七点
钟起床哦。
篇章填空 2
Dad: Sam, what time is it now?
Sam: It's (1) __________ __________! Oh no,
I'm almost late for school.
Dad: Calm down. It's just (2) __________
o'clock. You still have time.
Sam: Phew! What time does the class start?
Dad: At (3) __________ __________. And
you have a break at ten (4) __________.
Sam: Thanks, Dad. And I need to be home at
five (5) __________.
爸爸：山姆，现在几点了？
山姆：六点五十分了！哎呀，我上
学要迟到了。
爸爸：别慌，现在才六点钟，你还
有时间。
山姆：呼！那上课时间是几点？
爸爸：七点四十分。你还有个十点
四十分的课间休息哦。
山姆：谢谢爸爸。我还得在五点五
十分前到家。"""
img_url_t16 = "https://cdn.phototourl.com/free/2026-04-05-8ba25524-7339-461a-be94-9637ee45f4ee.png"
USER_STEM_t16 = """1. Share the time of daily ________.
分享日常活动的时间。
2. Make a ________ for your daily routine.
为你的日常作息制作一张时间表。
3. I read books at ________ ________.
我在九点十分读书。
4. I'm late! ________ up!
我迟到了！快点！
5. It's half past ________.
现在是九点半。
6. ________ ________! Hurry up!
我迟到了！快点！
7. Don't be ________.
不要迟到。
8. Make a timetable for your ________ ________.
为你的日常作息制作一张时间表。
9. ________ ________ ________ for your daily routine.
为你的日常作息制作一张时间表。
10. Share the time of ________ activities.
分享日常活动的时间。"""
img_url_t17 = "https://cdn.phototourl.com/free/2026-04-05-f6b00634-a56d-4804-8a0f-45266d1bea05.png"
USER_STEM_t17 = """Dad: Sam, don't be (1) __________ for school
again!
Sam: Oh no! (2) __________ __________! I
miss the school bus.
Dad: You need a (3) __________ plan.
Sam: Yes. Let's (4) __________ __________
__________ together.
Dad: Good idea! First, write down your (5)
__________ __________.
爸爸：山姆，上学别再迟到了！
山姆：哦不！我迟到了！我没赶上
校车。
爸爸：你需要一个日计划。
山姆：是的。我们一起制作一份时
间表吧。
爸爸：好主意！先把你的日常作息
写下来。"""
img_url_t18="https://cdn.phototourl.com/free/2026-04-05-f6b00634-a56d-4804-8a0f-45266d1bea05.png"
USER_STEM_t18 = """Dad: Sam, let's list your daily (1) __________
first.
Sam: Yes. And I also make a (2) __________
for them.
Dad: Nice! What time is your game time?
Sam: It's (3) __________ __________.
Dad: Oh, it's coming! (4) __________ up!
Let's go!
Sam: Wait! It doesn't start until (5)
__________ o'clock.
爸爸：山姆，我们先列出你的日常
活动吧。
山姆：好的。我还为这些活动做了
一份时间表。
爸爸：不错！你的游戏时间是几
点？
山姆：是九点十分。
爸爸：哦，快到点了！快点！我们
走吧！
山姆：等一下！要到九点钟才开始
呢。"""
img_url_t19="https://cdn.phototourl.com/free/2026-04-05-2cef9469-87c4-460c-aba9-a55c6dd580a7.png"
USER_STEM_t19 = """1. I don't mind a small ________.
我不介意一个小小的错误。
2. Let's work ________ the problem together.
让我们一起解出这道难题吧。
3. It's good to ________ ________ ________.
憧憬你的生活是一件美好的事。
4. Give a helping ________.
伸出援助之手。
5. It's okay to ________ ________.
犯错误是没关系的。
6. It's okay to ________ mistakes.
犯错误是没关系的。
7. Let's work out the problem ________.
让我们一起解出这道难题吧。
8. Let's ________ out the problem together.
让我们一起解出这道难题吧。
9. It's good to ________ your life.
憧憬你的生活是一件美好的事。
10. I ________ ________ papers.
我分发试卷。"""
img_url_t20="https://cdn.phototourl.com/free/2026-04-05-c23740ea-5247-4e96-a899-46a6aefa98c5.png"
USER_STEM_t20 = """Sam: Lucas, let's (1) ________ a nice poster
for our class!
Lucas: Great! We can do it (2) ________.
Sam: First, we need to (3) ________ hard on
the drawing.
Lucas: Yes! And we can draw a beautiful (4)
________ of our classroom.
Sam: After that, we will (5) ________
________ the poster to our classmates.
山姆：卢卡斯，我们一起为班级制
作一张漂亮的海报吧！
卢卡斯：好极了！我们可以一起做
这件事。
山姆：首先，我们要努力画好这幅
画。
卢卡斯：对！我们还可以画一张我
们教室的漂亮图画。
山姆：之后，我们要把这张海报分
发给同学们。
"""
img_url_t21 = "https://cdn.phototourl.com/free/2026-04-05-c23740ea-5247-4e96-a899-46a6aefa98c5.png"
USER_STEM_t21="""Sam: Lucas, don't worry. It's just a small (1)
__________.
Lucas: Thanks. Let's work it (2) __________
together.
Sam: Great! Can you (3) __________
__________ __________ at school?
Lucas: Sure! Please raise your (4) __________
if you know the answer.
Sam: It's OK to (5) __________ __________
when we learn English.
山姆：卢卡斯，别担心。这只是一
个小错误。
卢卡斯：谢谢。我们一起解决这个
错误吧。
山姆：太好了！你能想象一下你在
学校的生活吗？
卢卡斯：当然！如果你知道答案请
举手。
山姆：我们学英语的时候犯错是
没关系的。"""
img_url_t22 = "https://cdn.phototourl.com/free/2026-04-05-0ea39d5b-dd72-4e8c-a1c0-811353f1762a.png"
USER_STEM_t22 = """1. 句子填空
It’s __________ this Sunday, so we can’t have a picnic in the park.
这个周日下雨，所以我们不能去公园野餐了。
2. When the wind blows gently, I like to ________ ________ ________ in the square.
当风轻轻吹的时候，我喜欢在广场放风筝。
3. The weather is __________ in the evening, so I often take a walk after dinner.
晚上天气凉爽，所以我经常晚饭后散步。
4. It’s too hot in July—let’s __________ __________ __________ __________ to
swim and play sand.
七月太热了，我们去海滩游泳玩沙吧。
5. Look! The birds are starting to __________ back to the south as winter comes.
看！冬天来了，鸟儿开始飞回南方了。
6. Winter in Harbin is always __________ __________ __________.
哈尔滨的冬天总是寒冷多雪。
7. It’s __________ in the early morning of winter, so I wear a hat when I go to school.
冬天的清晨很冷，所以我上学时戴帽子。
8. Summer holidays are here, and the weather is __________ __________
__________.
暑假到了，天气炎热晴朗。
9. Autumn afternoons are often __________ __________ __________.
秋天的下午常常凉爽多雨。
10. It’s __________ today! Let’s go outside to make a big snowman with our classmates.
今天下雪了！我们出去和同学们堆个大雪人吧。"""
img_url_t23 = "https://cdn.phototourl.com/free/2026-04-05-0eadc7a5-0e1f-4f0b-a45a-04a20062af21.jpg"
USER_STEM_t23="""Alice: Sam, autumn is (1) __________. I like
it!
Sam: Yes! It’s not (2) __________ like
summer. Do you want to (3) __________
__________ __________?
Alice: No, I want to (4) __________
__________ __________ __________. The
beach is fun!
Sam: I like to (5) __________! Kites fly high
in cool wind.
篇章填空 1
爱丽丝：山姆，秋天很凉爽。我喜
欢它！
山姆：是的！它不像夏天那样多雨。
你想去放风筝吗？
爱丽丝：不，我想去海滩。海滩很
有趣！
山姆：我喜欢飞！风筝在凉爽的风
里飞得很高。"""
img_url_t23 = "https://cdn.phototourl.com/free/2026-04-05-0eadc7a5-0e1f-4f0b-a45a-04a20062af21.jpg"
USER_STEM_t23="""Alice: Sam, what's winter like in Harbin?
It’s (1) __________ __________
__________.
Sam: Yes! It’s really (2) __________. But
summer there is (3) __________
__________ __________.
Alice: What about autumn? Is it (4)
__________ __________ __________?
Sam: Sometimes! And it can be (5)
__________ in late autumn.
篇章填空 2
爱丽丝：山姆，哈尔滨的冬天怎
么样？又冷又下雪。
山姆：是的！真的很冷。但那里
的夏天炎热晴朗。
爱丽丝：秋天呢？是凉爽多雨的
吗？
山姆：有时候是！而且深秋可能
会下雪。"""
img_url = img_url_t23
USER_STEM = USER_STEM_t23



import asyncio

def main():
    """主函数：测试 recognize_xishuashua 功能"""
    asyncio.run(_main())

async def _main():
    """异步主函数"""
    
    print("=" * 60)
    print("测试 recognize_xishuashua 功能")
    print("=" * 60)
    print(f"图片路径: {img_url}")
    print(f"题干内容: {USER_STEM[:100]}...")
    print("=" * 60)
    
    try:
        status, result = await recognize_xishuashua_async(
            img_url=img_url,
            question_stem=USER_STEM
        )
        
        print("\n识别状态:")
        print(status)
        
        print("\n识别结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

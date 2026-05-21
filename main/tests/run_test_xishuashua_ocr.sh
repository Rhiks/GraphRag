# 同时发起 3 个请求
for i in {1..3}; do
  curl -X POST http://127.0.0.1:5300/xishuashua_ocr_recg \
  -H "Content-Type: application/json" \
  -d '{
    "img_url": "https://pic1.imgdb.cn/item/69bb8d76658eb5ba3df90bd5.jpg",
    "question_stem": "Sam: Hi, Lucas! Can I talk to (1) __________?\nLucas: Sure!\nSam: Do you like (2) __________?\nLucas: Yes! We must (3) __________\n__________ __________ __________ every\nday.\nSam: Great! What will we (4) __________ in\nthe English class (5) __________?\nLucas: We will talk about our morning\nroutines.\nSam: Lucas, what do you do (1) ________ you\nget up?\nLucas: I brush my teeth. Then I go (2)\n________ the classroom.\nSam: We can (3) ________ our English books\nthere.\nLucas: (4) ________ ________!\nSam: Thanks! By the way, let'\''s play together\ntomorrow.\nLucas: Great! (5) ________ ________\n________!"
  }'&
done
wait
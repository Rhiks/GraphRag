from gensim.models import KeyedVectors

# 加载词向量（示例：腾讯中文词向量）
wv = KeyedVectors.load_word2vec_format('tencent_embedding.bin', binary=True)

def find_semantic_candidates(word, topn=5):
    try:
        # 如果词在词表里，直接找最近邻
        similar_words = wv.most_similar(word, topn=topn)
        return [w for w, _ in similar_words]
    except KeyError:
        # 如果词不在词表，拆字计算（如 "方何" → "方" + "何" 的平均向量）
        if len(word) == 2:
            char1, char2 = word[0], word[1]
            if char1 in wv and char2 in wv:
                avg_vector = (wv[char1] + wv[char2]) / 2
                similar_words = wv.similar_by_vector(avg_vector, topn=topn)
                return [w for w, _ in similar_words]
        return []  # 无法处理

print(find_semantic_candidates("方何"))

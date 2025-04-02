from quiz_data import questions


def calculate_result(answers: dict) -> str:
    scores = {"a": 0, "б": 0, "в": 0, "г": 0}
    for key, answer in answers.items():
        for q in questions:
            if q["key"] == key:
                index = q["options"].index(answer)
                scores[list(q["scores"].values())[index]] += 1
                break

    max_score = max(scores.values())
    candidates = [k for k, v in scores.items() if v == max_score]

    return candidates[0] if len(candidates) == 1 else "equal"

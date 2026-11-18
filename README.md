# FactWeightAuto

팩트의 무게(@weight.of.facts) 카드뉴스를 인스타그램과 Threads에 자동으로 올리는 저장소예요.

## 흐름
1. Claude가 주제를 조사해 `content/번호-주제/post.json` 을 만들고 카드 그림(slide_1.png ...)과 미리보기(preview.png)를 그려요. 상태는 **draft**.
2. 사장님이 미리보기를 보고 "승인"하면 상태가 **approved** 로 바뀌어요.
3. GitHub Actions가 매시간 확인해서 `publish_at` 시간이 된 승인 글을 인스타·Threads에 동시에 올려요.
4. 매일 밤 댓글을 모아 `comments/inbox.json` 에 저장해요. 답글은 사장님 확인 후에만 올려요.

## 비밀값 (Settings → Secrets and variables → Actions)
| 이름 | 내용 |
|---|---|
| THREADS_TOKEN | Threads 열쇠 (메타 개발자 → WeightOfFacts Auto) |
| IG_TOKEN | 인스타 열쇠 (메타 개발자 → WeightOfFacts Cards) |
| IG_USER_ID | 인스타 계정 번호 |

## 손으로 실행하기
Actions → 카드뉴스 자동 업로드 → Run workflow
- check: 열쇠가 제대로 되는지만 확인
- now + 폴더: 그 글을 지금 바로 올림 (시험용)
- comments: 댓글 모으기

## 파일
- GUIDE.md: 글·사실·디자인 규칙
- scripts/render.py: 카드 그리기 (큰 글씨 디자인)
- scripts/publish.py: 올리기
- scripts/comments.py: 댓글 모으기

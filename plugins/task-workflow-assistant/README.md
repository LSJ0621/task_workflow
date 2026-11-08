# Task Workflow Assistant

`task-workflow`의 범용 스킬 위에 올라가는 개인 비서 하네스. **Claude Code 전용**이고 `task-workflow` 플러그인이 먼저 설치돼 있어야 한다.

지식 베이스(마크다운 git 저장소)를 연결하면 세 층으로 일한다.
비서 세션(사용자와 대화) → 팀장 세션(작업마다 하나) → 작업자·검수자 서브에이전트.

| 구성 | 역할 |
| --- | --- |
| `skills/setup-knowledge-base` | 지식 베이스를 초안으로 만들거나 기존 것을 연결한다 |
| `skills/run-assistant` | 비서. 지시를 받아 팀장 세션을 열고 두 줄 보고를 전달한다 |
| `skills/lead-task` | 팀장. 기준을 읽고 나누고 위임하고 검수자를 부른 뒤 400자로 보고한다 |
| `agents/criteria-checker` | 검수자. 산출물을 기준 문서와 대조해 판정하고 검수 결과 문서를 쓴다 |
| `skills/librarian` | 사서. 낮에는 메모 한 줄(쪽지), 밤에는 메모를 정식 기록으로(정리) |
| `skills/inspect-work` | 작업 점검. 사용자가 오늘 작업을 직접 보고 지적한다 |
| `templates/knowledge-base` | 지식 베이스 초안. 개인 내용은 없다 |

플러그인이 지식 베이스에 기대는 것은 네 가지뿐이다: 규칙 문서(`wiki/conventions.md`), 색인(`INDEX.md`), README의 불변 조건, 규칙 문서에 적힌 메모 위치. 나머지 구조는 각자 바꿔도 된다.

## 설치

```bash
claude plugin marketplace add LSJ0621/task_workflow
claude plugin install task-workflow@task-workflow-marketplace
claude plugin install task-workflow-assistant@task-workflow-marketplace
```

## 첫 설정

새 세션에서 `/task-workflow-assistant:setup-knowledge-base`를 실행한다. 새로 만들지 기존 저장소를 연결할지 묻고, 경로를 Claude Code 설정에 저장한다.

## 개인 정보

플러그인에는 초안과 절차만 있다. 실제 지식 베이스는 각자의 비공개 저장소에 둔다. 비밀값과 고객 인프라 식별자는 지식 베이스에도 적지 않는다.

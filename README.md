# Task Workflow

과제와 개인 프로젝트에서 사용할 Codex·Claude Code 스킬 12개와 Claude Code 서브에이전트 2개입니다.
특정 대회, 기술 스택, 문서 형식, 제한시간을 고정하지 않습니다.

| 스킬 | 사용하는 시점 |
| --- | --- |
| `setup-project-guidance` | 프로젝트 AGENTS.md 초안을 제안하고 검수 후 작성·갱신할 때 |
| `analyze-task` | 자료를 이해하고 요구사항·데이터·중요 질문을 정리할 때 |
| `maintain-work-notes` | 논의·결정을 기록하고 문서와 필요한 Git 이력으로 정리·재개할 때 |
| `collaborate-plan-execute` | 계획에 병렬·순차 작업을 반영하거나, 확정된 계획을 위임·통합할 때 |
| `verify-work` | 실제 결과물이 요구사항을 충족하는지 검사하고 핵심 구현을 이해할 때. Claude Code에서는 검증을 서브에이전트 `verifier`에 맡깁니다 |
| `build-screens` | 앱이나 웹의 화면을 만들거나 고칠 때. 시안과 다르게 만들게 될 때 묻기, 배치 문제 고치기, 실제 화면을 캡처해 확인하기 |
| `setup-knowledge-base` | 개인 지식 베이스를 초안으로 만들거나 기존 저장소를 연결하고 점검할 때 |
| `leave-memo` | 작업하는 세션이 사용자 피드백·결정·맥락을 지식 베이스에 메모 한 줄로 남기고, 프로젝트 상황판의 자기 묶음을 고치고, 쌓인 프로젝트 지침 후보를 가져갈 때 |
| `librarian` | 쌓인 메모를 정식 기록과 요약으로 정리하고 왜 그렇게 정리했는지 보고할 때, 주 1회 문서 구조를 점검할 때 |
| `analyze-context` | 쌓인 사례에서 실수가 난 원인을 추정해 에이전트가 묻지 않고 규칙(스킬, 훅, 전역 지침, 응답 양식)을 고치고, 추정을 적어 두었다가 틀리면 다시 볼 때(자가 발전). 사용자가 아침 보고서를 달라고 할 때 |
| `review-report` | 한 주 동안 규칙이 어떻게 바뀌었는지 모아 검증한 HTML 점검 보고서를 만들 때, 사용자가 그 보고서를 보고 피드백할 때 |
| `daily-upkeep` | 매일 새벽 예약 작업의 메인 세션이 사서 정리, 자가 발전, 아침 보고서 확인, 토요일 구조 점검·사용자 분석·점검 보고를 단계마다 서브에이전트에 넘길 때 |

지식 베이스 스킬을 뺀 나머지는 단독 사용이 가능합니다. 외부 MCP 서버, 개인 API 키가 필요하지 않습니다.
서브에이전트 정의 둘(`verifier`, `evolve-report-checker`)은 Claude Code에서만 씁니다. 만든 쪽이 아닌 눈으로 확인하는 일이라 따로 뜨고, 읽기와 검사 실행만 합니다. Codex처럼 서브에이전트 정의를 쓸 수 없는 곳에서는 같은 방법이 스킬에 있어 세션이 직접 합니다.
협업에는 실행 환경이 제공하는 내장 서브에이전트를 사용하고, 사용할 수 없으면 그 제약을 알린 뒤 순차 실행합니다.

## 지식 베이스 (선택)

`setup-knowledge-base`, `leave-memo`, `librarian`, `analyze-context`, `review-report`, `daily-upkeep` 여섯 스킬은 개인 지식 베이스(마크다운 git 저장소)가 있을 때만 씁니다.
지식 베이스는 개발뿐 아니라 생활·취향·상황까지, 에이전트가 모르는 사용자 맥락을 쌓는 곳입니다. 일하는 방법(규칙)은 스킬과 전역 지침에 있고, 지식 베이스에는 기록만 둡니다.
규칙은 에이전트가 쌓인 사례를 근거로 스스로 고칩니다(`analyze-context`). 사용자는 변경을 하나하나 검수하지 않습니다. 평일에는 달라고 할 때 아침 보고서로 에이전트가 무엇을 원인으로 보고 어떻게 고쳤는지를 보고, 주 1회 점검 보고서(`review-report`)로 확인합니다. 보안 규칙과 점검 장치만 바꾸기 전에 사용자에게 올립니다.

- 처음에는 새 세션에서 `setup-knowledge-base`를 호출합니다. 새로 만들지 기존 저장소를 연결할지 묻고, 위치를 Claude Code 설정(`~/.claude/settings.json`의 `env.KNOWLEDGE_BASE_DIR`)에 저장합니다. 사용자 설정 파일을 바꾸므로 실행 전에 알립니다.
- 스킬이 지식 베이스에 꼭 기대는 것은 색인(`INDEX.md`)과 메모 위치(`raw/journal/`) 두 가지뿐입니다. 맥락 요약(`wiki/context.md`)과 규칙별 사례표(`wiki/rule-cases.md`)는 권장입니다. 없으면 맥락 요약은 사서가 첫 정리 때, 사례표는 자가 발전이 처음 분류할 때 만듭니다. 나머지 구조는 바꿔도 됩니다.
- 사례·결정·맥락은 머리말 `scope`로 모든 프로젝트(`me`)인지 한 프로젝트(`project:<이름>`)인지 가릅니다. 맥락 요약과 프로젝트 카드는 줄마다 원본 id를 달아, 에이전트가 원본을 매번 다 읽지 않고 필요할 때 그 기록만 엽니다.
- 프로젝트 작업은 그 프로젝트 폴더에서 연 세션이 사용자와 직접 하고, 결과도 그 세션이 바로 알립니다. 작업 단위가 끝나면 그 세션이 지식 베이스 상황판(`wiki/board.md`)의 자기 프로젝트 묶음을 고칩니다(`leave-memo`). 자가 발전이 그 프로젝트에만 걸리는 규칙 후보를 묶음의 "지침 후보"에 적어 두면 그 세션이 프로젝트 지침으로 옮깁니다.
- 메모는 세션이 `leave-memo`로 적고 커밋만 합니다. 사용자 말과 에이전트가 이해한 뜻(풀이)을 나눠 적고, 적을 때 이해한 뜻을 사용자에게 한 줄로 보여 줍니다. 하루 한 번 정리(`librarian`)가 정식 기록으로 옮기고 맥락 요약과 카드를 갱신한 뒤 함께 push합니다. 사서는 사례를 분류하거나 규칙을 고치지 않습니다.
- 정리 다음에 자가 발전(`analyze-context`)이 새 사례를 규칙별 사례표에 한 줄씩 적고, 실수가 난 원인을 추정해 그 원인을 막는 방법으로 규칙을 고칩니다. 실수를 뒤집은 문장을 더하지 않고, 있는 문장을 고쳐 쓰거나 읽히는 곳으로 옮기는 것을 먼저 봅니다. 변경 하나에 커밋 하나를 남기고, 무엇을 원인으로 봤는지는 추정 기록(`~/.claude/evolve/hypotheses.md`)에, 그날 고친 것은 아침 보고서(`~/.claude/evolve/reports/`)에, 어디까지 봤는지는 상태 파일(`~/.claude/evolve/state.md`)에 적습니다. 다른 서브에이전트(`evolve-report-checker`)가 보고서의 근거와 실제 고친 내용을 확인합니다.
- 토요일에는 구조 점검(`librarian`의 구조 점검 절차), 사용자가 바라는 것을 분석한 기록 다시 보기, 점검 보고(`review-report`)도 돕니다. 구조 변경은 묻지 않고 머지합니다. 점검 보고서는 지식 베이스 `raw/reviews/YYYY-MM-DD.html`에 올라가고, 세 저장소(전역 설정, 플러그인, 지식 베이스)에 `review-YYYY-MM-DD` 태그가 로컬로 달립니다.
- 이 순서는 예약 작업 하나가 `daily-upkeep`을 따라 돌립니다. 메인 세션은 진행만 하고 단계마다 서브에이전트 하나에 넘깁니다.
- 지식 베이스를 찾지 못하면 이 스킬들은 아무것도 쓰지 않고 `setup-knowledge-base`를 안내합니다.
- 실제 지식 베이스는 각자의 비공개 저장소에 둡니다. 비밀값과 고객 인프라 식별자는 지식 베이스에도 적지 않습니다.

## GitHub에서 설치

플러그인 명령을 지원하는 Codex 터미널에서 실행합니다.

```bash
codex plugin marketplace add https://github.com/LSJ0621/task_workflow.git
codex plugin add task-workflow@task-workflow-marketplace
codex plugin list --json
```

설치 후 새 Codex 채팅 또는 CLI 세션을 시작합니다. CLI에서는 `/plugins`에서도 설치 상태를 확인할 수 있습니다.
COFA 등 다른 컴퓨터에서도 해당 Codex 버전과 운영 정책이 이 설치 방식을 지원해야 합니다.

## Claude Code에서 설치

```bash
claude plugin marketplace add LSJ0621/task_workflow
claude plugin install task-workflow@task-workflow-marketplace
```

설치 후 새 Claude Code 세션을 시작합니다. 스킬 본문은 Codex와 같은 파일을 사용합니다.

## 사용 예시

```text
$analyze-task 첨부 자료와 @참조한 데이터를 분석해줘. 내가 이해할 설명과 중요한 질문까지만 제시해줘.

$maintain-work-notes 합의한 내용과 미정 사항의 상세를 주제별 문서에 기록하고 INDEX.md는 문서 안내 목차로 갱신해줘. 진행을 지속적으로 관리할 필요가 있으면 STATUS.md에 요약과 링크를 남겨줘.

$maintain-work-notes INDEX로 문서 위치를 찾고 STATUS가 있으면 본문을 읽어 현재 상태와 다음 작업을 파악해줘. 이후 요청에서는 STATUS만 해시로 확인하고, 바뀌었거나 읽은 맥락을 기억하지 못하면 STATUS와 필요한 주제 문서를 읽어줘. 구현은 시작하지 마.

$maintain-work-notes STATUS에 남은 작업이 모두 완료됐다면 필요한 결정·근거를 주제 문서에 남기고 Git 보존을 확인한 뒤 완료 내용을 비워줘. 파일과 INDEX 링크는 유지해줘.

$setup-project-guidance 이 프로젝트의 자료와 기존 지침을 확인해서 AGENTS.md 초안과 근거를 제안해줘. 아직 파일에 반영하지 마.

$setup-project-guidance 방금 검수한 초안을 AGENTS.md에 반영해줘. 기존 지침과 사용자 변경은 보존해줘.

$maintain-work-notes 문서를 재정리해줘. 중요한 결정 이유는 유지하고 과거 원문은 확인된 커밋과 당시 경로로 연결해줘.

$collaborate-plan-execute 계획만 작성해줘. 작업 의존관계, 파일 담당 범위, 병렬·순차 실행과 통합 기준을 포함해줘.

$collaborate-plan-execute 확정된 계획을 실행해줘. 독립 작업을 내장 에이전트에 위임하고 결과를 통합해줘.

$analyze-context 지난 실행 뒤에 쌓인 사례를 분류하고 규칙을 고쳐줘. 넣기 전에 판단 결과를 먼저 보여줘.

$review-report 점검하자. 가장 최근 점검 보고서를 열어줘.

$daily-upkeep 매일 정리 순서를 돌려줘. 점검 보고도 돌린다.

$verify-work 현재 구현이 요구사항을 만족하는지 검사해줘. 프로젝트 기록이 있으면 INDEX·STATUS로 기준 문서를 찾아 현재 내용을 확인하고, 없으면 내가 제공한 요구사항을 사용해줘. 검증만 하고 소스·테스트·설계 파일은 추가하거나 수정하지 마.
```

일반 요청에서도 관련 스킬이 선택될 수 있습니다. 확실히 지정하려면 Codex에서는 `$스킬이름`, Claude Code에서는 `/task-workflow:스킬이름`을 사용하세요.
스킬 선택 자체가 계획 전용 요청을 실행 요청으로 바꾸지는 않습니다.
해시 비교는 STATUS.md에만 적용합니다. 다른 문서의 최신 내용·결정 이유는 주제별 문서에 유지하고, 정확한 과거 원문·변경 전후는 필요할 때 Git에서 확인합니다. 다른 세션에 영향을 주는 중요한 문서 변경은 STATUS에 짧은 요약과 링크로 반영합니다.
설치만으로 모든 세션이나 compact 이후에 규칙이 자동 실행되는 것은 아닙니다. AGENTS 연결이 없는 세션에서는 새 세션·compact 후 `$maintain-work-notes`를 다시 호출하세요. 프로젝트 AGENTS 작성·갱신은 `setup-project-guidance`에 요청합니다. 기본은 초안 제안까지이고 검수한 내용의 반영 요청이 있어야 파일을 수정합니다. 설치·업데이트만으로 AGENTS.md나 전역 설정을 변경하지 않습니다.

## 설치 후 직접 확인

1. 새 세션에서 스킬을 하나씩 명시해 호출하고 의도한 역할로 작동하는지 확인합니다.
2. 가상 자료로 분석을 요청하고, 사실·가정·질문이 구분되는지 확인합니다.
3. 샘플 논의를 기록한 뒤 INDEX가 문서 안내만 담는지, STATUS는 필요한 경우에만 생성되고 진행 요약과 링크를 담는지 확인합니다. 다른 세션에서 INDEX → STATUS가 있으면 본문 확인 → 관련 주제별 문서 순으로 재개해봅니다. 같은 세션에서는 STATUS 해시가 같고 읽은 맥락이 남아 있으면 STATUS 본문 재읽기를 생략하고, 바뀌었거나 기억이 없으면 다시 읽는지 확인합니다. 주제 문서의 해시를 주기적으로 검사하지 않는지도 확인합니다. 완료 정리 후에도 파일·INDEX 링크가 유지되는지 확인합니다.
4. 계획만 요청했을 때 제품 코드·설정 수정이나 구현 작업 에이전트 실행이 없는지 확인합니다. 필요한 읽기 전용 탐색 에이전트는 허용됩니다.
5. 실행과 검증에서는 수정 범위, 실제 검사 결과, 미확인 항목을 확인합니다. 검증만 요청했을 때 소스·테스트·설계 파일을 추가·수정하지 않는지도 확인합니다.
6. 설정 스킬에 초안만 요청했을 때 파일이 바뀌지 않는지 확인합니다. 검수 후 반영을 요청했을 때 기존 지침과 실제 문서 위치가 보존되고, 존재하지 않는 INDEX·STATUS·기술스택 문서를 만들거나 연결하지 않는지 확인합니다. Claude Code 연결도 검수한 범위에서만 적용합니다.
7. 새 세션에서 AGENTS 지침이 로드되는지 확인하고, 실제 compact 뒤 기록 스킬 사용과 STATUS 변경 감지까지 별도로 확인합니다. 문구 추가만으로 자동 복구가 검증됐다고 판단하지 않습니다.

이 저장소의 배포 과정에서는 사용자 Codex에 실제 설치하거나 설치 후 호출하는 테스트를 수행하지 않았습니다.

AGENTS.md의 기록 스킬 사용 안내는 프로젝트 지침이며 실행 훅이 아닙니다. compact 후 자동 복구의 실제 동작은 별도 검증이 필요합니다. [AGENTS.md 공식 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## 파일 구성

- `.agents/plugins/marketplace.json`: GitHub 저장소를 설치 목록으로 등록하기 위한 설정.
- `plugins/task-workflow/plugin.json`: 표준 플러그인 manifest.
- `plugins/task-workflow/.codex-plugin/plugin.json`: Codex 호환 manifest. 같은 이름·버전·표시 정보를 유지합니다.
- `.claude-plugin/marketplace.json`: Claude Code 설치 목록 설정.
- `plugins/task-workflow/.claude-plugin/plugin.json`: Claude Code manifest. 같은 이름·버전을 유지합니다.
- `plugins/task-workflow/skills/`: 스킬 지침과 필요할 때만 읽는 참고 지침.
- `plugins/task-workflow/hooks/`: 플러그인 훅 설정(`hooks.json`)과 훅이 돌리는 스크립트. 지금은 사용자 입력에 질문이 있으면 무엇을 채우고 무엇을 뺄지의 기준이 있는 곳을 알려 주는 훅 하나가 있습니다. 입력을 막지 않습니다.
- `plugins/task-workflow/agents/`: Claude Code 서브에이전트 정의. `verifier`(결과물 검증)와 `evolve-report-checker`(자가 발전 아침 보고서 확인)가 있습니다.
- 각 스킬의 `agents/openai.yaml`: UI 표시 정보이며 커스텀 서브에이전트 정의가 아닙니다.
- `plugins/task-workflow/skills/setup-knowledge-base/assets/knowledge-base/`: 지식 베이스 초안. 개인 내용은 없고 `{{...}}` 자리표시자를 `scripts/bootstrap.py`가 치환합니다.
- `plugins/task-workflow/skills/librarian/references/`: 메모 형식·기록 형식·정리 절차·구조 점검 절차·구조 변경 브랜치 머지·글쓰기 규칙과 기록 틀. `scripts/`에 식별자 계산과 불변 조건 점검 스크립트가 있습니다.
- `plugins/task-workflow/skills/analyze-context/references/`: 자가 발전의 판단 방법, 추정 기록과 아침 보고서의 형식, 토요일 사용자 분석 절차.
- `plugins/task-workflow/skills/review-report/references/`: 점검 보고의 단계별 지침(분석, 검증, 만들기)과 단계 사이에 오가는 초안·판정의 형식. `assets/`에 보고서 HTML 틀이 있습니다.

기록 스킬의 참조는 작업별로 나눕니다.
- `reading.md`: 문서 탐색·재개·STATUS 해시 확인. 분석·검증도 이 읽기 규칙을 공유합니다.
- `organization.md`: 문서 역할·기록 내용·결정 기록 형식·폴더·분리·이동·링크.
- `status.md`: 필요한 STATUS의 생성·갱신·완료 정리.
- `history.md`: 문서와 Git의 보존 경계·과거 원문 조회·출처·커밋.

설정 스킬의 `references/project-guidance.md`는 AGENTS에 넣을 지침의 선별·연결·기존 내용 보존 기준을 관리합니다. 기록 스킬은 AGENTS 설정을 담당하지 않습니다.

각 스킬 본문은 필요한 참조를 안내하며, 읽기만 할 때 작성·완료 정리 지침까지 일괄 로드하지 않습니다.

프로젝트별 작업 기록은 이 플러그인을 사용하는 프로젝트 안에 생성합니다.
- `INDEX.md`: 문서별 상대경로 링크·목적·다루는 내용·읽어야 할 상황만 안내하는 목차.
- `STATUS.md`: 필요한 경우 프로젝트의 기존 기록 위치에서 하나를 사용하며, 진행 중·완료 표시, 현재 단계·다음 작업·진행 장애와 문서 링크를 짧게 관리. 완료 내용은 필요한 근거와 Git 원문 보존 후 비우고, 파일·INDEX 링크는 유지.
- 주제별 문서: 기획·설계·정책·검증의 상세 내용·결정 근거·미정 사항.
- 프롬프트: 이번 세션의 구체적인 요청과 추가 지시. 지속적인 진행 정보는 필요한 기록에 반영.

INDEX에 서비스·정책·진행 요약이나 새 세션용 작업 지침을 넣지 않습니다. 기존 혼합 문서는 정보와 결정 상태를 보존하며 역할별로 분리하고 링크를 갱신합니다.
STATUS 변경 확인에는 `git hash-object --no-filters -- <STATUS 경로>`를 사용하고 `-w`는 쓰지 않습니다. 커밋하지 않은 내용도 비교하며, 해시를 문서에 저장하거나 번호를 수동 갱신하지 않습니다. STATUS에 반영되지 않은 다른 문서 변경을 자동 감지하지는 않습니다. 해시는 변경 확인용이고, 완료 내용을 지우기 전 Git 원문 보존 확인은 별도입니다.
플러그인 소스에는 실제 과제, 개인 데이터, 작업 기록을 포함하지 않습니다.

## 수정 후 업데이트

스킬과 참고 지침을 수정하고 세 manifest의 버전을 함께 올린 뒤 GitHub에 업로드합니다.
사용자 환경에서는 먼저 설치 출처인 Git 저장소를 새로 가져옵니다.

```bash
codex plugin marketplace upgrade task-workflow-marketplace
```

Codex CLI 0.166.0에서는 이 명령이 새 Git 마켓플레이스 스냅샷을 가져오면 그 마켓플레이스의 설치된 플러그인 캐시도 함께 갱신합니다. 일반 업데이트에 삭제·재설치는 필요하지 않습니다.

갱신이 성공한 뒤 새 Codex 채팅 또는 CLI 세션을 시작해 변경된 스킬을 사용합니다. CLI에서는 `/new`로 새 채팅을 시작할 수 있습니다.
이 과정은 설치된 플러그인과 캐시를 갱신하며 프로젝트 안의 작업 기록이나 개인 `AGENTS.md`를 수정하는 작업은 아닙니다.
메뉴로 관리하려면 `/plugins`에서 Task Workflow 마켓플레이스를 선택하고 표시되는 Upgrade 기능을 사용합니다. 정확한 메뉴 표시는 Codex 버전에 따라 다를 수 있습니다.
오류가 발생하면 오류 메시지와 Codex 버전을 먼저 확인합니다. 제거·재설치는 일반 업데이트 절차가 아니라 문제 해결이 필요한 경우의 선택지입니다.

동작 근거: [Codex 0.166.0 마켓플레이스·설치 캐시 갱신 구현](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core-plugins/src/manager.rs#L3026-L3108).

Claude Code에서는 다음 명령으로 갱신하고 새 세션을 시작합니다.

```bash
claude plugin marketplace update task-workflow-marketplace
claude plugin update task-workflow@task-workflow-marketplace
```

## 참고

- [플러그인 패키징과 배포](https://developers.openai.com/plugins/build/plugins)
- [Codex 플러그인 명령](https://learn.chatgpt.com/docs/developer-commands#codex-plugin)

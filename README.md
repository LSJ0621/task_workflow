# Task Workflow

과제와 개인 프로젝트에서 사용할 독립적인 Codex 스킬 4개입니다.
특정 대회, 기술 스택, 문서 형식, 제한시간을 고정하지 않습니다.

| 스킬 | 사용하는 시점 |
| --- | --- |
| `analyze-task` | 자료를 이해하고 요구사항·데이터·중요 질문을 정리할 때 |
| `maintain-work-notes` | 논의·결정을 기록하고 문서와 필요한 Git 이력으로 정리·재개할 때 |
| `collaborate-plan-execute` | 계획에 병렬·순차 작업을 반영하거나, 확정된 계획을 위임·통합할 때 |
| `verify-work` | 실제 결과물이 요구사항을 충족하는지 검사하고 핵심 구현을 이해할 때 |

각 스킬은 단독 사용이 가능합니다. 커스텀 에이전트, 외부 MCP 서버, 개인 API 키가 필요하지 않습니다.
협업에는 실행 환경이 제공하는 내장 서브에이전트를 사용하고, 사용할 수 없으면 그 제약을 알린 뒤 순차 실행합니다.

## GitHub에서 설치

플러그인 명령을 지원하는 Codex 터미널에서 실행합니다.

```bash
codex plugin marketplace add https://github.com/LSJ0621/task_workflow.git
codex plugin add task-workflow@task-workflow-marketplace
codex plugin list --json
```

설치 후 새 Codex 채팅 또는 CLI 세션을 시작합니다. CLI에서는 `/plugins`에서도 설치 상태를 확인할 수 있습니다.
COFA 등 다른 컴퓨터에서도 해당 Codex 버전과 운영 정책이 이 설치 방식을 지원해야 합니다.

## 사용 예시

```text
$analyze-task 첨부 자료와 @참조한 데이터를 분석해줘. 내가 이해할 설명과 중요한 질문까지만 제시해줘.

$maintain-work-notes 지금까지 합의한 내용과 미해결 쟁점을 기록하고 INDEX.md를 갱신해줘.

$maintain-work-notes 기존 기록을 읽고 현재 상태와 다음 작업을 파악해줘. 구현은 시작하지 마.

$maintain-work-notes 문서를 재정리해줘. 중요한 결정 이유는 유지하고 과거 원문은 확인된 커밋과 당시 경로로 연결해줘.

$collaborate-plan-execute 계획만 작성해줘. 작업 의존관계, 파일 담당 범위, 병렬·순차 실행과 통합 기준을 포함해줘.

$collaborate-plan-execute 확정된 계획을 실행해줘. 독립 작업을 내장 에이전트에 위임하고 결과를 통합해줘.

$verify-work 현재 구현이 요구사항을 만족하는지 검사하고 핵심 데이터 흐름을 짧게 설명해줘.
```

일반 요청에서도 관련 스킬이 선택될 수 있습니다. 확실히 지정하려면 `$스킬이름`을 사용하세요.
스킬 선택 자체가 계획 전용 요청을 실행 요청으로 바꾸지는 않습니다.

## 설치 후 직접 확인

1. 새 세션에서 스킬을 하나씩 명시해 호출하고 의도한 역할로 작동하는지 확인합니다.
2. 가상 자료로 분석을 요청하고, 사실·가정·질문이 구분되는지 확인합니다.
3. 샘플 논의를 기록한 뒤 다른 세션에서 INDEX를 통해 재개해봅니다.
4. 계획만 요청했을 때 파일 수정이나 에이전트 실행이 없는지 확인합니다.
5. 실행과 검증에서는 수정 범위, 실제 검사 결과, 미확인 항목을 확인합니다.

이 저장소의 배포 과정에서는 사용자 Codex에 실제 설치하거나 설치 후 호출하는 테스트를 수행하지 않았습니다.

## 파일 구성

- `.agents/plugins/marketplace.json`: GitHub 저장소를 설치 목록으로 등록하기 위한 설정.
- `plugins/task-workflow/plugin.json`: 표준 플러그인 manifest.
- `plugins/task-workflow/.codex-plugin/plugin.json`: Codex 호환 manifest. 같은 이름·버전·표시 정보를 유지합니다.
- `plugins/task-workflow/skills/`: 스킬 지침과 필요할 때만 읽는 참고 지침.
- 각 스킬의 `agents/openai.yaml`: UI 표시 정보이며 커스텀 서브에이전트 정의가 아닙니다.

프로젝트별 `INDEX.md`와 작업 기록은 이 플러그인을 사용하는 프로젝트 안에 생성합니다.
플러그인 소스에는 실제 과제, 개인 데이터, 작업 기록을 포함하지 않습니다.

## 수정 후 업데이트

스킬과 참고 지침을 수정하고 두 manifest의 버전을 함께 올린 뒤 GitHub에 업로드합니다.
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

## 참고

- [플러그인 패키징과 배포](https://developers.openai.com/plugins/build/plugins)
- [Codex 플러그인 명령](https://learn.chatgpt.com/docs/developer-commands#codex-plugin)

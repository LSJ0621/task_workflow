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

$maintain-work-notes 합의한 내용과 미정 사항의 상세를 주제별 문서에 기록하고 INDEX.md는 문서 안내 목차로 갱신해줘. 진행을 지속적으로 관리할 필요가 있으면 STATUS.md에 요약과 링크를 남겨줘.

$maintain-work-notes INDEX로 문서 위치를 찾고 STATUS가 있으면 본문을 읽어 현재 상태와 다음 작업을 파악해줘. 이후 요청에서는 첫 줄의 revision이 바뀌었을 때만 본문을 다시 읽어줘. 구현은 시작하지 마.

$maintain-work-notes STATUS에 남은 작업이 모두 완료됐다면 필요한 결정·근거를 주제 문서에 남기고 Git 보존을 확인한 뒤 완료 내용을 비워줘. 파일과 증가하는 revision은 유지해줘.

$maintain-work-notes 문서를 재정리해줘. 중요한 결정 이유는 유지하고 과거 원문은 확인된 커밋과 당시 경로로 연결해줘.

$collaborate-plan-execute 계획만 작성해줘. 작업 의존관계, 파일 담당 범위, 병렬·순차 실행과 통합 기준을 포함해줘.

$collaborate-plan-execute 확정된 계획을 실행해줘. 독립 작업을 내장 에이전트에 위임하고 결과를 통합해줘.

$verify-work 현재 구현이 요구사항을 만족하는지 검사하고 핵심 데이터 흐름을 짧게 설명해줘.
```

일반 요청에서도 관련 스킬이 선택될 수 있습니다. 확실히 지정하려면 `$스킬이름`을 사용하세요.
스킬 선택 자체가 계획 전용 요청을 실행 요청으로 바꾸지는 않습니다.
STATUS 변경 번호 확인은 해당 스킬로 상태를 공유하는 세션의 절차입니다. 설치만으로 모든 세션에서 매 요청 자동 실행되는 것은 아니므로 필요한 세션에 사용을 지시합니다. AGENTS.md나 전역 설정을 자동 추가하지 않습니다.

## 설치 후 직접 확인

1. 새 세션에서 스킬을 하나씩 명시해 호출하고 의도한 역할로 작동하는지 확인합니다.
2. 가상 자료로 분석을 요청하고, 사실·가정·질문이 구분되는지 확인합니다.
3. 샘플 논의를 기록한 뒤 INDEX가 문서 안내만 담는지, STATUS는 필요한 경우에만 생성되고 진행 요약과 링크를 담는지 확인합니다. 다른 세션에서 INDEX → STATUS가 있으면 본문 확인 → 관련 주제별 문서 순으로 재개해봅니다. 같은 세션에서는 번호가 같을 때 본문 재읽기를 생략하고, 변경됐거나 기억이 없으면 다시 읽는지 확인합니다. 완료 정리 후에도 파일·INDEX 링크·계속 증가하는 번호가 유지되는지 확인합니다.
4. 계획만 요청했을 때 파일 수정이나 에이전트 실행이 없는지 확인합니다.
5. 실행과 검증에서는 수정 범위, 실제 검사 결과, 미확인 항목을 확인합니다.

이 저장소의 배포 과정에서는 사용자 Codex에 실제 설치하거나 설치 후 호출하는 테스트를 수행하지 않았습니다.

## 파일 구성

- `.agents/plugins/marketplace.json`: GitHub 저장소를 설치 목록으로 등록하기 위한 설정.
- `plugins/task-workflow/plugin.json`: 표준 플러그인 manifest.
- `plugins/task-workflow/.codex-plugin/plugin.json`: Codex 호환 manifest. 같은 이름·버전·표시 정보를 유지합니다.
- `plugins/task-workflow/skills/`: 스킬 지침과 필요할 때만 읽는 참고 지침.
- 각 스킬의 `agents/openai.yaml`: UI 표시 정보이며 커스텀 서브에이전트 정의가 아닙니다.

프로젝트별 작업 기록은 이 플러그인을 사용하는 프로젝트 안에 생성합니다.
- `INDEX.md`: 문서별 상대경로 링크·목적·다루는 내용·읽어야 할 상황만 안내하는 목차.
- `STATUS.md`: 필요한 경우 프로젝트의 기존 기록 위치에서 하나를 사용하며, 첫 줄 `revision: N`과 진행 중·완료 표시, 현재 단계·다음 작업·진행 장애와 문서 링크를 짧게 관리. 완료 내용은 필요한 근거와 Git 원문 보존 후 비우고, 파일·변경 번호는 유지.
- 주제별 문서: 기획·설계·정책·검증의 상세 내용·결정 근거·미정 사항.
- 프롬프트: 이번 세션의 구체적인 요청과 추가 지시. 지속적인 진행 정보는 필요한 기록에 반영.

INDEX에 서비스·정책·진행 요약이나 새 세션용 작업 지침을 넣지 않습니다. 기존 혼합 문서는 정보와 결정 상태를 보존하며 역할별로 분리하고 링크를 갱신합니다.
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

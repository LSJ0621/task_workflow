# 지침 장치 표

확인한 날짜: 2026-11-23. 문서가 바뀌면 다시 확인한다.

규칙이나 지침을 어디에 둘지 고를 때 본다. 도구마다 지침을 둘 수 있는 장치와 그 장치가 언제 읽히는지를 공식 문서에서 옮겼다.
"확인"은 그날 그 문서를 열어 본 줄이다. 열어 본 문서에서 찾지 못한 것은 "확인 못 함"이라고 적었다. 표에 없는 동작을 기억으로 채우지 않는다.

## 어디에 둘지 고르는 순서

### 1. 언제 읽혀야 하는지로 가른다

가르는 선은 그 규칙이 언제 읽혀야 하느냐다. 위에서부터 보고 처음 맞는 줄을 고른다.

| 그 규칙은 | 두는 곳 |
| :- | :- |
| 예외 없이 매번 일어나야 한다 | 훅이나 설정. 지침 파일은 읽히기만 하고 강제되지 않는다 |
| 어떤 프로젝트, 어떤 요청에서든 지킨다 | 전역 지침. 말하는 방식이면 응답 양식(Claude Code) |
| 특정 종류의 일을 할 때만 따르는 여러 단계 방법이다 | 스킬 |
| 그 프로젝트의 어떤 작업에서든 지킨다 | 루트 프로젝트 지침 |
| 한 폴더 안에서만 지킨다 | 그 폴더의 하위 폴더 지침 |
| 폴더가 아니라 파일 종류나 이름 규칙에 걸린다 | 경로 조건 규칙(Claude Code만) |
| 일을 맡은 작업자가 지킨다 | 서브에이전트 정의 |

### 2. 늘 읽히는 곳은 짧게 둔다

늘 읽히는 곳은 길수록 덜 지켜진다.

- Claude Code 문서는 CLAUDE.md를 파일 하나에 200줄 아래로 두라고 한다. 더 길면 컨텍스트를 더 쓰고 덜 지켜진다고 적는다.
- Codex는 지침 파일을 합친 크기가 32KiB(`project_doc_max_bytes` 기본값)에 닿으면 그 뒤 파일을 넣지 않는다. 문서는 AGENTS.md를 작게 두라고 한다.
- Claude Code 문서는 SKILL.md를 500줄 아래로 두고 자세한 내용은 따로 둔 파일로 옮기라고 한다.
- 파일을 나눠도 늘 읽히는 장치면 읽히는 양은 그대로다. `@` 가져오기와 `paths`가 없는 규칙 파일이 그렇다.
- 늘 읽히는 곳이 길어지면 한 폴더나 한 종류의 일에만 걸리는 내용부터 하위 폴더 지침, 경로 조건 규칙, 스킬로 옮긴다.

### 3. 같은 내용을 두 곳에 두지 않는다

- 두 곳이 어긋나면 Claude는 아무 쪽이나 따를 수 있다고 문서에 있다.
- 다른 파일의 내용이 필요하면 복사하지 않는다. 그 파일을 가리키거나 가져온다.

### 4. 두 도구를 같이 쓰는 저장소에서는 AGENTS.md 하나를 같이 읽게 한다

같이 지킬 내용은 `AGENTS.md`에 둔다. Codex는 기본값에서 `CLAUDE.md`를 읽지 않는다.

Claude Code가 `AGENTS.md`를 읽는 조건은 아래와 같다.

- 작업 폴더와 그 위 폴더에 `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`가 하나도 없으면 `AGENTS.md`를 직접 읽는다(v2.1.277 이상). 하위 폴더의 `AGENTS.md`도 그 폴더의 파일을 열 때 읽는다.
- 셋 중 하나라도 있으면 기본 설정에서는 `AGENTS.md`를 읽지 않는다. 이때는 `AGENTS.md` 옆 `CLAUDE.md`의 첫 줄에 `@AGENTS.md`를 둔다. Claude Code에만 걸리는 내용은 그 아래에 쓴다. 하위 폴더도 같은 방법을 쓴다.
- 설정의 Project instructions 값을 `claude-md-and-agents-md`로 바꾸면 둘 다 읽는다. 이 값은 프로젝트 설정 파일에서는 무시된다. 그래서 저장소에 올려 같이 쓸 수 없다.
- `CLAUDE.md`를 `AGENTS.md`의 심볼릭 링크로 두는 방법도 문서에 있다. Windows에서 깨질 수 있고 Claude Code에만 걸리는 내용을 넣을 수 없다.

두 도구가 다르게 읽는 곳은 아래와 같다.

- 하위 폴더 지침은 읽히는 때가 다르다. Claude Code는 그 폴더의 파일을 다룰 때 읽는다. Codex는 그 폴더나 그 아래에서 시작했을 때만 읽는다. 저장소 루트에서 시작한 Codex도 지켜야 하는 내용은 루트 `AGENTS.md`에 둔다.
- `.claude/rules/`와 응답 양식은 Claude Code만 읽는다. Codex도 지켜야 하는 내용을 여기에만 두지 않는다.
- Claude Code는 `AGENTS.override.md`와 `.agents/` 아래를 읽지 않는다.
- 스킬은 두 도구가 같은 `SKILL.md` 형식을 쓰고 두는 폴더만 다르다. 두 문서 모두 스킬 폴더가 심볼릭 링크여도 따라간다고 적는다. Claude Code에만 있는 머리말 필드는 Codex 문서에 없다.

## Claude Code

| 장치 | 어디에 두나 | 언제 읽히나 | 무엇을 두기에 맞나 | 공식 문서 |
| :- | :- | :- | :- | :- |
| 전역 지침 | `~/.claude/CLAUDE.md` | 세션 시작. 모든 프로젝트 | 어떤 프로젝트, 어떤 요청에서든 지킬 것. 원칙만 짧게 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 전역 규칙 | `~/.claude/rules/*.md` | `paths`가 없으면 세션 시작. 있으면 맞는 파일을 다룰 때. 프로젝트 규칙보다 먼저 읽힌다 | 모든 프로젝트에서 특정 파일 종류에만 걸리는 개인 규칙 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 프로젝트 지침 | `./CLAUDE.md` 또는 `./.claude/CLAUDE.md` | 세션 시작. 작업 폴더와 그 위 폴더의 것을 모두 읽어 위 폴더부터 이어 붙인다. 서로 덮어쓰지 않는다. 루트의 것은 compact 뒤 다시 읽힌다 | 그 프로젝트의 어떤 작업에서든 지킬 것. 빌드·테스트 명령, 관례, 구조 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 개인 프로젝트 지침 | `./CLAUDE.local.md`. `.gitignore`에 넣는다 | 세션 시작. 같은 폴더의 `CLAUDE.md` 바로 뒤 | 저장소에 올리지 않을 개인 설정. 이 파일이 있으면 `AGENTS.md`를 직접 읽지 않는다 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 하위 폴더 지침 | `<폴더>/CLAUDE.md` | 그 폴더의 파일을 읽거나 쓰거나 고칠 때. 세션 시작에는 읽히지 않는다. 파일이 한도(20만 토큰 창에서 4만 자)를 넘으면 앞부분만 읽힌다(v2.1.309 이상) | 그 폴더(패키지, 서비스) 안에서만 지킬 것 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 규칙 파일(조건 없음) | `.claude/rules/*.md`. 하위 폴더로 나눠도 된다 | 세션 시작. `.claude/CLAUDE.md`와 같은 우선순위 | 프로젝트 지침을 주제별 파일로 나눌 때. 읽히는 양은 줄지 않는다 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 경로 조건 규칙 | `.claude/rules/*.md`의 머리말에 `paths`(glob 목록) | 맞는 파일을 읽거나 쓰거나 고칠 때. compact 뒤에는 맞는 파일을 다시 다룰 때 | 파일 종류나 이름 규칙에 걸리는 것. 테스트 파일, API 처리 코드처럼 여러 폴더에 흩어진 파일의 규칙 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| `@` 가져오기 | CLAUDE.md 안에 `@경로`. 상대 경로는 그 파일 기준. 네 단계까지 | 가져오는 CLAUDE.md가 읽힐 때 같이 | 다른 파일을 복사하지 않고 끌어올 때. 읽히는 양은 줄지 않는다. 작업 폴더 밖 파일은 처음에 허락을 묻는다 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| `AGENTS.md` | 저장소 루트와 하위 폴더 | 위 "두 도구를 같이 쓰는 저장소" 절의 조건에서만 | 다른 도구와 같이 지킬 프로젝트 지침 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 스킬 | `~/.claude/skills/<이름>/SKILL.md`, `.claude/skills/`, `<폴더>/.claude/skills/`, 플러그인의 `skills/` | 이름과 `description`은 목록으로 늘 읽힌다(창의 1%까지, 항목당 1,536자). 본문은 불렸을 때만 읽힌다. 하위 폴더의 스킬은 그 폴더의 파일을 다룬 뒤에 목록에 오른다. `paths`를 쓰면 맞는 파일을 다룰 때 켜진다 | 특정 종류의 일을 할 때 따르는 여러 단계 방법. 긴 참고 자료 | [skills](https://code.claude.com/docs/en/skills) 확인 |
| 응답 양식 | `~/.claude/output-styles/`, `.claude/output-styles/`, 플러그인의 `output-styles/`. 설정의 `outputStyle`로 고른다 | 요청마다 함께 보낸다. 서브에이전트에는 걸리지 않는다(fork는 걸린다) | 어떤 대화에서든 지킬 말투, 길이, 형식 | [output-styles](https://code.claude.com/docs/en/output-styles) 확인 |
| 훅 | 설정 파일, 플러그인의 `hooks/hooks.json`, 스킬·서브에이전트의 머리말 | 읽히는 것이 아니라 정한 때(도구 호출 앞뒤, 세션 시작 등)에 Claude Code가 실행한다. 세션 시작 훅과 프롬프트 제출 훅의 출력은 컨텍스트에 들어간다 | 예외 없이 매번 일어나야 하는 것. 막기, 검사, 형식 맞추기 | [hooks](https://code.claude.com/docs/en/hooks) 확인 |
| 서브에이전트 정의 | `.claude/agents/`, `~/.claude/agents/`, 플러그인의 `agents/` | 그 서브에이전트가 뜰 때 본문이 시스템 프롬프트가 된다. CLAUDE.md도 같이 읽힌다(내장 Explore, Plan은 뺀다). 응답 양식과 메인에서 부른 스킬은 넘어가지 않는다. `skills` 필드에 적은 스킬은 본문이 처음부터 들어간다 | 그 역할을 맡을 때마다 지킬 것 | [sub-agents](https://code.claude.com/docs/en/sub-agents) 확인 |
| 설정 파일 | `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json` | 읽히는 것이 아니라 Claude Code가 강제한다 | 지침이 아니다. 권한(막을 명령과 경로), 환경 변수, 훅 등록 | [settings](https://code.claude.com/docs/en/settings) 확인 |
| 시스템 프롬프트 덧붙이기 | 실행할 때 `--append-system-prompt`, `--append-system-prompt-file` | 그 실행에서만. 시스템 프롬프트 끝에 붙는다 | 스크립트나 예약 실행에 넣는 지침 | [cli-reference](https://code.claude.com/docs/en/cli-reference) 확인 |
| 자동 메모리 | `~/.claude/projects/<프로젝트>/memory/MEMORY.md` | 세션 시작에 앞 200줄 또는 25KB. Claude가 스스로 쓴다 | 규칙을 두는 곳이 아니다 | [memory](https://code.claude.com/docs/en/memory) 확인 |
| 조직 관리 지침 | 운영체제의 관리 위치에 둔 `CLAUDE.md` | 세션 시작. 전역 지침보다 먼저 | 조직이 모든 사용자에게 내려보내는 지침 | [memory](https://code.claude.com/docs/en/memory) 확인 |

- 세션 시작에 읽힌 파일은 `/context all`의 Memory files 목록에 나온다. 하위 폴더 지침은 이 목록에 나오지 않고, 읽힐 때 터미널에 `Loaded` 줄이 나온다. `InstructionsLoaded` 훅으로 무엇이 언제 읽혔는지 남길 수 있다.

## Codex

공식 문서 주소 `developers.openai.com/codex`는 지금 `learn.chatgpt.com/docs`로 넘어간다.

| 장치 | 어디에 두나 | 언제 읽히나 | 무엇을 두기에 맞나 | 공식 문서 |
| :- | :- | :- | :- | :- |
| 전역 지침 | `~/.codex/AGENTS.md`(`CODEX_HOME`을 정했으면 그 폴더) | 실행을 시작할 때 한 번. 모든 저장소 | 어떤 저장소에서든 지킬 것. 말하는 방식 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 확인 |
| 전역 덮어쓰기 | `~/.codex/AGENTS.override.md` | 있으면 전역 `AGENTS.md` 대신 이 파일만 읽는다 | 전역 지침을 지우지 않고 잠깐 바꿀 때 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 확인 |
| 저장소 루트 지침 | `<저장소 루트>/AGENTS.md` | 실행을 시작할 때 한 번. 루트에서 작업 폴더까지 내려가며 폴더마다 파일 하나를 읽어 이어 붙인다. 합친 크기가 32KiB에 닿으면 멈춘다 | 그 저장소의 어떤 작업에서든 지킬 것. 빌드·테스트 명령, 관례 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 확인 |
| 하위 폴더 지침 | `<폴더>/AGENTS.md` | 그 폴더나 그 아래에서 Codex를 시작했을 때만. 작업 폴더보다 아래에 있는 폴더는 찾지 않는다 | 그 폴더에서 시작해 하는 일에만 걸리는 것 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 확인 |
| 폴더 덮어쓰기 | `<폴더>/AGENTS.override.md` | 있으면 같은 폴더의 `AGENTS.md` 대신 이 파일만 읽는다 | 한 폴더의 지침을 통째로 바꿀 때 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 확인 |
| 다른 이름의 지침 파일 | `config.toml`의 `project_doc_fallback_filenames`에 파일 이름을 넣는다 | 그 폴더에 `AGENTS.md`가 없을 때 대신 읽는다 | 이미 다른 이름의 지침 파일을 쓰는 저장소 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 확인 |
| 스킬 | `.agents/skills/`(작업 폴더에서 저장소 루트까지), `~/.agents/skills/`, `/etc/codex/skills`, 플러그인 | 이름, `description`, 경로는 처음 목록으로 읽힌다(창의 2%까지). 본문은 골랐을 때만 읽힌다 | 되풀이하는 일의 여러 단계 방법 | [build-skills](https://learn.chatgpt.com/docs/build-skills) 확인 |
| 훅 | `~/.codex/hooks.json`, 신뢰한 프로젝트의 `.codex/hooks.json`, `config.toml`의 `[hooks]`, 플러그인 | 읽히는 것이 아니라 정한 때에 Codex가 실행한다. 세션 시작 훅과 프롬프트 제출 훅의 출력은 컨텍스트에 들어간다 | 예외 없이 매번 일어나야 하는 것 | [hooks](https://learn.chatgpt.com/docs/hooks) 확인 |
| 사용자 지정 에이전트 | `~/.codex/agents/*.toml`, `.codex/agents/*.toml`의 `developer_instructions` | 그 에이전트가 뜰 때 | 그 역할을 맡을 때마다 지킬 것 | [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) 확인 |
| 설정의 지침 값 | `~/.codex/config.toml`, 신뢰한 프로젝트의 `.codex/config.toml`. `developer_instructions`는 지침을 더하고 `model_instructions_file`은 내장 지침을 바꾼다 | 세션에 넣는다고만 적혀 있다. 자세한 때는 확인 못 함 | 지침 파일로 둘 수 없을 때만 | [config-reference](https://learn.chatgpt.com/docs/config-file/config-reference) 확인 |
| 명령 규칙 | `~/.codex/rules/*.rules` | 읽히는 것이 아니라 Codex가 강제한다. 실험 기능 | 지침이 아니다. 샌드박스 밖에서 돌릴 명령을 허용하거나 묻거나 막는다. Claude Code의 `.claude/rules/`와 이름만 같다 | [rules](https://learn.chatgpt.com/docs/agent-configuration/rules) 확인 |
| 메모리 | 그 컴퓨터의 메모리 저장소 | Codex가 스스로 쓰고 꺼낸다 | 규칙을 두는 곳이 아니다. 문서도 꼭 지킬 지침은 `AGENTS.md`에 두라고 한다 | [memories](https://learn.chatgpt.com/docs/customization/memories) 확인 |
| 사용자 지정 프롬프트 | `~/.codex/prompts/` | 직접 불렀을 때만 | 쓰지 않는다. 문서가 더는 권하지 않고 스킬을 쓰라고 한다 | [custom-prompts](https://learn.chatgpt.com/docs/custom-prompts) 확인 |
| 경로 조건 규칙 | 확인 못 함 | 확인 못 함 | 파일 종류에 걸리는 규칙은 가장 가까운 폴더의 `AGENTS.md`에 둔다 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)와 [rules](https://learn.chatgpt.com/docs/agent-configuration/rules)에 없다. 확인 못 함 |
| 지침 파일 안의 가져오기 | 확인 못 함 | 확인 못 함 | 쓰지 않는다 | [agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)에 없다. 확인 못 함 |
| 응답 양식 | 확인 못 함 | 확인 못 함 | 말하는 방식은 전역 `AGENTS.md`에 둔다 | [customization](https://learn.chatgpt.com/docs/customization/overview)에 없다. 확인 못 함 |

## 이 플러그인이 따로 정한 것

도구 문서에 있는 내용이 아니다. 이 플러그인을 쓰는 곳의 약속이다.

| 곳 | 두는 것 | 언제 읽히나 |
| :- | :- | :- |
| 플러그인 스킬 | 특정 분야나 종류의 일(화면 만들기, 검증, 기록)을 할 때 따르는 방법 | 그 일을 할 때 |
| 플러그인의 지식 베이스 스킬(`leave-memo`, `write-records`, `librarian`) | 지식 베이스를 적고 정리하는 방식 | 메모를 남길 때, 기록을 만들고 정리할 때 |
| 프로젝트 지침과 그 프로젝트의 다른 장치 | 그 프로젝트에서만 지킬 것. 그 프로젝트에서 일하는 세션이 고친다. 규칙을 스스로 고치는 쪽은 직접 고치지 않고 지식 베이스 상황판의 그 프로젝트 묶음에 후보로 적는다(`leave-memo` 스킬 "프로젝트 지침 후보" 절) | 그 프로젝트에서 |
| 지식 베이스 | 규칙을 두지 않는다. 지킬 것이 아니라 알 것만 있다. 요약 문서와 색인은 정리 단계가 만드는 것이라 직접 고치지 않는다 | 필요할 때 |

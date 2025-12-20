# Bug Fixes - Agent Guidelines

## 프로젝트 구조 원칙

### 파일 구조 규칙
```
프로젝트 루트/
├── character.py          # Character 기본 클래스만
├── game_state.py         # Player, NPC, GameState 클래스
├── utils.py              # 공통 유틸리티 함수
├── gemini_dm.py          # GeminiDM 클래스와 notify_dm
├── data_loader.py        # 데이터 로딩 전용
├── rag_manager.py        # RAG 시스템
├── main.py               # 메인 게임 루프
├── ui.py                 # UI 프레임
└── config.py             # 설정 상수
```

### Import 순서 규칙
모든 파일에서 다음 순서를 따릅니다:
```python
# 1. 표준 라이브러리
import os
import json
import random

# 2. 서드파티 라이브러리
import google.generativeai as genai
from dotenv import load_dotenv

# 3. 타입 힌트 (TYPE_CHECKING)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_state import GameState

# 4. 로컬 모듈
from utils import roll_dice
from config import SETTING_NAME
```

### 순환 Import 방지 규칙

**의존성 계층**:
```
Level 0: utils.py, config.py (의존성 없음)
Level 1: character.py (utils만 의존)
Level 2: game_state.py (character, utils 의존)
Level 3: gemini_dm.py, data_loader.py (game_state 의존 가능)
Level 4: main.py, ui.py (모든 것 의존 가능)
```

**규칙**:
- 하위 레벨은 상위 레벨을 import하지 않음
- 타입 힌트만 필요한 경우 `TYPE_CHECKING` 사용
- 순환 참조가 필요하면 함수 내부에서 import

## 코딩 스타일 가이드

### 클래스 설계 원칙

#### Character 클래스 (character.py)
```python
class Character:
    """기본 캐릭터 클래스 - 전투 관련 기능만"""
    
    필수 속성:
    - id, name, max_hp, current_hp
    - combat_stats, base_damage_dice
    - status_effects (리스트)
    
    필수 메서드:
    - is_alive() -> bool
    - take_damage(amount: int)
    - heal(amount: int)
    - attack(target: Character) -> str
    - tick_status_effects() -> list[str]
    - apply_status_effect(effect: dict)
```

#### Player 클래스 (game_state.py)
```python
class Player(Character):
    """플레이어 전용 - 인벤토리, 스킬, 퀘스트 등"""
    
    추가 속성:
    - inventory, equipment
    - ability_scores, skills_list
    - spell_slots
    - faction_reputations (딕셔너리)
    - active_quests, completed_quests
    
    추가 메서드:
    - equip_item(), use_item()
    - perform_skill_check()
    - cast_spell()
    - change_faction_reputation()
```

#### NPC 클래스 (game_state.py)
```python
class NPC(Character):
    """NPC 전용 - 대화 시스템"""
    
    추가 속성:
    - dialogue_responses
    - active_time_periods
    - is_currently_active
    
    추가 메서드:
    - get_dialogue_node(key: str) -> dict | None
```

### 에러 처리 원칙

#### 1. 파일 로딩 에러
```python
try:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    logging.warning(f"File not found: {filepath}")
    return default_value
except json.JSONDecodeError:
    logging.error(f"Invalid JSON in {filepath}")
    return default_value
except Exception as e:
    logging.error(f"Unexpected error loading {filepath}: {e}")
    return default_value
```

#### 2. API 호출 에러
```python
try:
    response = api_call()
    return response
except APIError as e:
    logging.error(f"API error: {e}")
    return fallback_response
except Exception as e:
    logging.error(f"Unexpected error: {e}")
    return error_response
```

#### 3. 게임 로직 에러
```python
# 방어적 프로그래밍
if not isinstance(player, Player):
    logging.error(f"Invalid player type: {type(player)}")
    return False, "Invalid player"

if item_id not in game.items:
    logging.warning(f"Item not found: {item_id}")
    return False, f"Item '{item_id}' not found"
```

### 로깅 규칙

```python
import logging

# 레벨별 사용
logging.debug("상세한 디버그 정보")      # 개발 중에만
logging.info("일반 정보")               # 정상 동작
logging.warning("경고 - 계속 진행")     # 데이터 누락 등
logging.error("에러 - 기능 실패")       # 기능 동작 실패
logging.critical("치명적 에러")         # 프로그램 중단 필요
```

### 타입 힌트 규칙

```python
# 기본 타입
def function(name: str, count: int) -> bool:
    pass

# 옵셔널
from typing import Optional
def function(value: str | None) -> Optional[int]:
    pass

# 리스트, 딕셔너리
def function(items: list[str], data: dict[str, int]) -> list[dict]:
    pass

# 클래스 타입 (순환 참조 방지)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_state import GameState

def function(game: 'GameState') -> None:
    pass
```

## 수정 작업 시 체크리스트

### 코드 수정 전
- [ ] 해당 파일의 현재 import 구조 확인
- [ ] 의존성 계층 확인 (순환 참조 방지)
- [ ] 수정할 클래스/함수가 다른 곳에서 어떻게 사용되는지 확인

### 코드 수정 중
- [ ] Import 순서 규칙 준수
- [ ] 타입 힌트 추가
- [ ] 에러 처리 추가
- [ ] 로깅 추가
- [ ] 기존 코드 스타일 유지

### 코드 수정 후
- [ ] 수정한 파일이 import 에러 없이 로드되는지 확인
- [ ] 관련된 다른 파일들도 여전히 작동하는지 확인
- [ ] 간단한 테스트 코드로 검증
- [ ] 로그 메시지가 적절한지 확인

## 테스트 전략

### 단위 테스트 (각 함수/메서드)
```python
# 예시: character.py의 heal() 테스트
char = Character("test", "Test", 100, {}, "1d6")
char.current_hp = 50
char.heal(30)
assert char.current_hp == 80, "Heal should increase HP"

char.heal(50)
assert char.current_hp == 100, "Heal should not exceed max_hp"
```

### 통합 테스트 (여러 컴포넌트)
```python
# 예시: 전투 시스템
player = Player(player_data)
npc = NPC(npc_data)
game = GameState(player)

# 전투 시작
result = start_combat(player, [npc], game)
assert "Combat started" in result

# 공격
attack_msg = player.attack(npc)
assert "attacks" in attack_msg or "misses" in attack_msg
```

### 수동 테스트 (실제 게임 플레이)
```bash
# 테스트 모드로 실행
set RUNNING_INTERACTIVE_TEST=true
python main.py

# 일반 모드로 실행
python main.py
```

## 커밋 메시지 규칙

```
[타입] 간단한 설명

상세 설명 (선택)

관련 이슈: AC-XXX
```

**타입**:
- `fix`: 버그 수정
- `feat`: 새 기능
- `refactor`: 리팩토링
- `docs`: 문서 수정
- `test`: 테스트 추가
- `style`: 코드 스타일 변경

**예시**:
```
fix: character.py에 누락된 메서드 추가

- heal() 메서드 구현
- tick_status_effects() 메서드 구현
- apply_status_effect() 메서드 구현
- utils.roll_dice import 추가

관련 이슈: AC-001
```

## 주의사항

### 절대 하지 말아야 할 것
1. ❌ 하위 레벨에서 상위 레벨 import (순환 참조)
2. ❌ 타입 힌트 없이 복잡한 함수 작성
3. ❌ 에러 처리 없이 파일/API 접근
4. ❌ 전역 변수에 직접 할당 (main.py 제외)
5. ❌ 기존 데이터 파일 구조 변경

### 반드시 해야 할 것
1. ✅ 모든 import는 파일 상단에
2. ✅ 타입 힌트 추가
3. ✅ 적절한 에러 처리
4. ✅ 의미 있는 로그 메시지
5. ✅ 수정 후 간단한 테스트

## 각 Phase별 주의사항

### Phase 1 (Critical Fixes)
- character.py 수정 시 game_state.py의 Player/NPC 클래스와 충돌 없는지 확인
- ITEM_DATABASE 수정 시 모든 참조 위치 검색 필수
- GeminiDM 통합 시 기존 mock 코드 완전히 제거

### Phase 2 (High Priority)
- faction_reputations 속성 추가 시 기존 save/load 로직 확인
- 에러 처리 추가 시 기존 동작 변경하지 않도록 주의

### Phase 3 (Medium Priority)
- 순환 import 해결 시 모든 파일의 import 순서 재확인
- 전역 변수 정리는 신중하게 (선택적 작업)

### Phase 4 (Low Priority)
- 사소한 수정이지만 전체 동작 확인 필수

## 문제 발생 시 대응

### Import 에러
1. 의존성 계층 다이어그램 확인
2. TYPE_CHECKING 사용 검토
3. 함수 내부 import 검토

### 런타임 에러
1. 로그 메시지 확인
2. 타입 체크 (isinstance)
3. None 체크 추가

### 테스트 실패
1. 수정 전 상태로 롤백
2. 작은 단위로 다시 수정
3. 각 단계마다 테스트

## 완료 기준

각 Task 완료 시:
- [ ] 코드가 에러 없이 실행됨
- [ ] 관련 기능이 정상 작동함
- [ ] 로그 메시지가 적절함
- [ ] 다른 기능에 영향 없음

전체 Phase 완료 시:
- [ ] 모든 Critical 버그 수정됨
- [ ] 게임이 시작부터 종료까지 작동함
- [ ] 기본 게임플레이 가능 (대화, 전투, 아이템)
- [ ] 테스트 모드 정상 작동

# Procedural KTY Generator

**Версия:** 1.2

Процедурный генератор картонных тарных ящиков (КТЯ) для Blender.

## Назначение

Генератор создаёт параметрические 3D-модели транспортной тары для:

- симуляции автоматизированных складов
- цифровых двойников логистических систем
- моделирования работы AGV
- визуализации складских процессов
- генерации тестовых окружений

## Структура проекта

```
KTY-generator/

├── main.py              # Точка входа для Blender
├── launcher.py          # Обёртка для запуска
├── src/
│   ├── __init__.py      # Пакет
│   ├── kty.py           # Главный класс KTY (API)
│   ├── geometry.py      # Генерация геометрии коробки
│   ├── materials.py     # Материал картона
│   ├── states.py        # Состояния (closed/open/damaged)
│   ├── lod.py           # Уровни детализации (LOD)
│   ├── export.py        # Экспорт в .blend/.obj/.fbx/.glb
│   ├── render.py        # Рендеринг PNG
│   ├── metadata.py      # JSON-метаданные
│   ├── cli.py           # Парсер CLI-аргументов
│   └── config.py        # YAML-конфигурация
├── configs/
│   ├── high.yaml        # Пример конфигурации High
│   ├── ultra_low.yaml   # Ultra Low для массовой симуляции
│   └── damaged.yaml     # Повреждённая коробка
├── exports/             # Сюда сохраняются экспортированные модели
├── renders/             # Сюда сохраняются рендеры
└── README.md
```

## Требования

- [Blender](https://www.blender.org/) 3.0+
- Python 3.10+ (встроенный в Blender)
- PyYAML (опционально, для конфигурационных файлов)

## Быстрый старт

### Запуск через Blender

```bash
blender --background --python main.py -- \
    --quality high \
    --state closed \
    --size 600x400x400
```

### Запуск через launcher.py

```bash
python launcher.py --quality high --state damaged --seed 42
```

### Запуск с конфигурационным файлом

```bash
blender --background --python main.py -- \
    --config configs/high.yaml
```

## Параметры CLI

| Флаг | Значения | По умолчанию | Описание |
|------|----------|-------------|----------|
| `--quality` | `ultra-low`, `low`, `medium`, `high`, `ultra-high` | `medium` | Уровень детализации |
| `--state` | `closed`, `open`, `damaged` | `closed` | Состояние коробки |
| `--size` | Формат `LxWxH` | `600x400x400` | Размер коробки (мм) |
| `--config` | Путь к файлу | — | YAML-конфигурация |
| `--no-export` | — | — | Отключить экспорт |
| `--no-render` | — | — | Отключить рендер |
| `--seed` | Целое число | — | Seed для повторяемости |
| `--count` | Целое число | `1` | Пакетная генерация |

## Уровни детализации (LOD)

| LOD | Полигонов | Толщина | Клапаны | Детали |
|-----|-----------|---------|---------|--------|
| Ultra Low | 6-12 | Нет | Нет | Только форма |
| Low | 50-100 | 1 мм | Нет | Базовая форма |
| Medium | 500-1000 | 3 мм | Да | Линии сгиба, швы |
| High | 2000-5000 | 3 мм | Да | Внутренняя поверхность |
| Ultra High | 5000-20000 | 3 мм | Да | Микродефекты |

## Состояния

### CLOSED
Закрытая коробка. Стандартное транспортное состояние.

### OPEN
Открытая коробка с регулируемым углом клапанов (0-180°).

### DAMAGED
Повреждённая коробка. Уровень повреждений от 0.0 до 1.0.

## Программный API

```python
from src.kty import KTY

# Создание коробки
box = KTY(
    size=(600, 400, 400),
    quality="high",
    state="closed",
    seed=42,
)

# Генерация
box.generate()

# Экспорт
box.export(output_dir="exports")

# Рендер
box.render(output_dir="renders")
```

## Экспорт

Все модели сохраняются в директорию `exports/`:

- `.blend` — обязательный формат (содержит mesh, материалы, камеру, освещение)
- `.obj` — дополнительный
- `.fbx` — дополнительный
- `.glb` — дополнительный
- `.json` — метаданные

Формат имени: `KTY_{quality}_{state}.*`

## Метаданные

```json
{
    "id": "KTY_000001",
    "type": "CARTON_BOX",
    "dimensions": { "x": 600, "y": 400, "z": 400 },
    "emptyWeight": 0.7,
    "state": "closed",
    "quality": "high",
    "content": "external",
    "generatedAt": "2025-01-01T00:00:00",
    "formatVersion": "1.2"
}
```

## Пакетная генерация

```bash
blender --background --python main.py -- \
    --quality ultra-low \
    --count 10000
```

## Масса пустой коробки

Масса рассчитывается автоматически на основе размеров:
- Удельная плотность гофрокартона: ~0.7 кг/м²
- Коэффициент нахлёстов и клапанов: 15%

Для коробки 600×400×400 мм масса ≈ 0.70 кг.

## Примеры

### Создание повреждённой коробки

```bash
blender --background --python main.py -- \
    --quality high \
    --state damaged \
    --size 600x400x400 \
    --seed 42
```

Результат:
```
exports/
    KTY_high_damaged.blend
    KTY_high_damaged.obj
    KTY_high_damaged.json

renders/
    KTY_high_damaged.png
```

### Массовая симуляция 1000 коробок

```bash
blender --background --python main.py -- \
    --quality ultra-low \
    --state closed \
    --count 1000 \
    --no-render
```

## Интеграция с Product Generator

Данный генератор создаёт только тару. Товары генерируются отдельным модулем **Product Generator** и размещаются внутри КТЯ внешней системой управления складом.

## Лицензия

MIT

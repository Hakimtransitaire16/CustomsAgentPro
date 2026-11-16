# قاعدة المعرفة الرسمية

المراجع الرسمية التي يعتمد عليها CustomsAgentPro: الوثائق الأصلية، نصها الكامل، وبياناتها المنظمة القابلة للبحث وللاستعمال في المحرك.

📊 **[التحليل الكامل](ANALYSE.md)**

## المحتوى

| المجلد | المحتوى |
| --- | --- |
| `sources/` | الملفات الأصلية PDF (8) |
| `text/` | النص المستخرج |
| `data/` | البيانات المنظمة JSON / CSV |
| `tools/` | سكربتات الاستخراج والبناء والبحث |

| الوثيقة | البيانات |
| --- | --- |
| التعريفة الجمركية DGD 2016 | `tarif_2016.json` · `tarif_2016.csv` (15 946 سطراً) · `tarif_2016_notes.json` (ملاحظات الفصول) |
| مجموعة قرارات التصنيف 2025 | `decisions_classement_2025.json` (77 RTC + 6 نموذج 110) |
| مجموعة قرارات التصنيف 2020 | `decisions_classement_2020.json` (105 RTC + 18 قراراً آخر) |
| قانون المالية 2026 (القانون 25-17) | `loi_finances_2026.json` (176 مادة) · `mesures_tarifaires_lf2026.json` (10 تدابير) |
| القانون 17-04 المعدّل لقانون الجمارك | `loi_17-04_code_douanes.json` |
| المرسوم التنفيذي 18-165 (القرارات المسبقة) | `decret_18-165.json` |
| EBTI (الاتحاد الأوروبي) · تقرير الجمارك الذكية (منظمة الجمارك العالمية 2024) | نص كامل في فهرس البحث |

## إضافة مصادر جديدة

📚 **[المرجع الكامل للمصادر](REFERENTIEL.md)**: 47 مرجعاً، مع حالة كل واحد ورابطه الرسمي.

```bash
python tools/ingest.py ~/Downloads/douane/     # يتعرف على الملفات، يستخرج النص (OCR إن كان مسحاً ضوئياً)، يبنيها ويفهرسها
python tools/ingest.py --rapport               # ما الموجود وما الناقص
```

## الاستعمال

```bash
cd knowledge-base
python tools/kb.py search "climatiseur split"     # بحث في كل الوثائق (بالفرنسية)
python tools/kb.py code 8415.90                   # أسطر التعريفة + قرارات نفس البند
python tools/kb.py article "50 ter"               # مادة من القانون أو المرسوم
python tools/kb.py stats
```

في المحرك:

```python
from customsagent.engine import Engine
engine = Engine.official()          # تعريفة 2016 + نسب قانون المالية 2026 + قرارات 2020 و2025
engine.classify("Boitier unité extérieure climatiseur")
```

والخادم: `CUSTOMSAGENT_DATA=official python -m customsagent.server`

## إعادة البناء

```bash
tools/extract_text.sh        # PDF -> text (poppler-utils)
python tools/build_kb.py     # text -> data/ + kb.sqlite
```

## ⚠️ حدود

- **تعريفة 2016 ليست التعريفة السارية.** 11 رمزاً من قرارات 2025 غير موجودة فيها. المحرك يطبّق فوقها النسب غير المشروطة لقانون المالية 2026 (المواد 131 و139 و140). تحقق دائماً من التعريفة السارية.
- الحق الجمركي فقط: لا TVA ولا DAPS في التعريفة. المحرك يفترض TVA بـ19 % ويضع علامة على ذلك.
- القرارات الرسمية بلا اسم الحامل: تُستعمل كسوابق للتوجيه، والقرار يلزم حامله فقط.
- قرارا RTC 025 و026 فيهما خطأ في الرمز داخل المنشور نفسه. البيانات تحمل تحذيراً (`warnings`).

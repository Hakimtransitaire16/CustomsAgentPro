# النموذج الأولي — "ملف واحد، يقين كامل"

محرك تحليل لملف الشحنة، مبني على نموذج البيانات المستخرج في [الدراسة](../docs/etude/04-synthese-et-modele.md).

## ماذا يفعل
| الوحدة | الملف | الدور |
|---|---|---|
| نموذج البيانات | `customsagent/models.py` | الملف، البنود، الوثائق، الأطراف، القرارات (على غرار WCO DM / EUCDM) |
| التصنيف | `customsagent/classifier.py` | اقتراح رمز HS بالعربية أو الفرنسية، مع درجة ثقة والسوابق (RTC/BTI) |
| القرارات | `customsagent/knowledge.py` | سجل RTC/BTI: السريان، الانتهاء، القرارات المملوكة للمتعامل |
| قواعد العمل | `customsagent/compliance.py` | R-RTC، R-EUDR، R-CBAM، R-DOC، R-VAL، R-LIC |
| التكلفة | `customsagent/duties.py` | القيمة لدى الجمارك، الحق الجمركي، DAPS، TVA، التكلفة النهائية |
| الواجهة | `web/index.html` + `customsagent/server.py` | واجهة عربية (RTL) + واجهة برمجية JSON |

## التشغيل (Python 3.10+ فقط، بدون مكتبات خارجية)
```bash
cd app
python -m customsagent.server          # ثم افتح http://localhost:8000
python -m unittest discover -s tests   # 24 اختباراً
```

## الواجهة البرمجية
```
POST /api/classify   {"description": "Plaquettes de frein céramique"}
POST /api/analyze    {"direction": "import", "origin_country": "CN", "destination_country": "DZ",
                      "exchange_rate": 150, "freight": 800, "holder_nif": "...",
                      "items": [{"description": "...", "hs_code": "8708.30", "value": 12000}],
                      "documents": [{"type": "invoice", "number": "F1"}]}
```
النتيجة: `status` (ready / review / blocked)، `findings` (القاعدة، الخطورة، الرسالة، البند)، `cost` (للاستيراد).

## ⚠️ حدود هذا النموذج
- **التعريفة والنسب توضيحية** (`data/tariff_sample.json`)، وليست التعريفة الرسمية ولا قانون المالية الساري.
- **القرارات تجريبية** (`data/rulings_sample.json`، مراجعها تبدأ بـ`DEMO-`)، وليست قرارات حقيقية للمديرية العامة للجمارك أو EBTI.
- نطاقا EUDR و CBAM **مبسّطان** على مستوى البنود (4 أرقام). المرجع هو الملحقان الرسميان.
- التصنيف مبني على تطابق الكلمات. سيُستبدل في المرحلة M2 بنموذج لغوي مع السوابق كمرجع.
- كل اقتراح هو **أداة مساعدة للوكيل المعتمد**، والقرار والمسؤولية له.

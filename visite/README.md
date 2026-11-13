# محرّك المعاينة الجمركية — `visite`

**ملف JSON واحد ← كل المخرجات.** تُنقل بيانات الملف من الصور الممسوحة مرة واحدة، ثم يُنتج المحرّك آلياً: البطاقة التقنية PDF، وصفحة المعاينة على الهاتف، والسجلّ مع لوحة المتابعة. ويتحقق كل مرة من الحسابات ومن تطابق الأرقام مع الصور.

## الطبقات الأربع

| الطبقة | الملفات | الدور |
|---|---|---|
| 1 · البيانات | `schema/dossier.schema.json` · `data.py` | مصدر الحقيقة الوحيد لكل ملف + التحقق من البنية |
| 2 · المولّد | `calc.py` · `ocr.py` · `render.py` · `verify.py` · `templates/fiche.html.j2` | 15 فحصاً آلياً، OCR، مطابقة الأرقام مع الصور، PDF بالنموذج الأوروبي، إعادة قراءة الـ PDF |
| 3 · الهاتف | `mobile.py` · `templates/visite.html.j2` | صفحة معاينة تعمل دون إنترنت: قائمة تحقق، عدّ، صور، محضر ← تصدير JSON |
| 4 · السجلّ | `registry.py` · `templates/dashboard.html.j2` | سجلّ JSON + CSV (Excel / Power BI) ولوحة متابعة |
| ⭐ الكل في واحد | `app.py` · `templates/cockpit.html.j2` | تطبيق موحّد في ملف HTML واحد |

## ⭐ التطبيق الموحّد (ملف واحد)

`python -m visite app dossiers/X/dossier.json` يُنتج **ملف HTML واحد** يجمع المخرجات الخمسة ويعمل دون إنترنت على الهاتف والحاسوب:

| التبويب | المحتوى |
|---|---|
| البطاقة | البطاقة التقنية كاملة (A4) ← زر «طباعة / حفظ PDF» |
| المعاينة | قائمة التحقق، العدّ (مطابق / فرق)، الصور بالكاميرا، المحضر ← **يُكتب مباشرة داخل البطاقة** |
| الفحوص | 15 فحصاً آلياً + مطابقة الأرقام مع الصور |
| السجلّ | لوحة المتابعة وجدول الملفات |
| البيانات | تنزيل ملف JSON للملف، السجلّ CSV، ملف JSON للمعاينة، البطاقة مع المحضر |

## الأوامر

```bash
python -m visite extraire  dossiers/X/dossier.json   # OCR ← اقتراحات المراجع (حاوية، MRN، D10…)
python -m visite controler dossiers/X/dossier.json   # الفحوص الآلية
python -m visite fiche     dossiers/X/dossier.json   # OCR + مطابقة + PDF + إعادة القراءة
python -m visite mobile    dossiers/X/dossier.json   # صفحة المعاينة للهاتف
python -m visite pv        dossiers/X/dossier.json visite_X.json   # إدخال المعاينة (محضر + صور) في الـ PDF
python -m visite registre  dossiers/X/dossier.json   # السجلّ + لوحة المتابعة
python -m visite app       dossiers/X/dossier.json   # التطبيق الموحّد (ملف واحد)
python -m visite tout      dossiers/X/dossier.json   # الكل
```

المخرجات في `dossiers/X/sortie/`، والسجلّ في `dossiers/registre/`.

## الفحوص الآلية (`calc.py`)
مبلغ الفاتورة = البنود + الشحن · التحويل إلى الدينار · مجموع البنود · التأمين · تصفية كل بند (CS، DD، وعاء TVA، TVA) · التصفية الإجمالية · الوزن الصافي والقائم · عدد الطرود · الكمية × السعة · التوطين البنكي قبل الشحن · المدة بين الرسو والتصريح مقارنة بمهلة الحاوية · رقم المراقبة للحاوية (ISO 6346).

## ⚠️ سرية بيانات الزبائن
هذا المستودع **عام**. لا تُرفع إليه الملفات الحقيقية أبداً، فهي تحتوي NIF وRC وبيانات بنكية ومبالغ. المجلد `dossiers/` مستثنى في `.gitignore`. المثال `exemples/dossier_exemple.json` وهمي بالكامل.

## الاختبارات
```bash
python -m unittest visite.tests.test_visite -v    # 10 اختبارات
```
المتطلبات: Python 3.10+، jinja2، jsonschema، Pillow، pytesseract (مع tesseract)، playwright (مع Chromium)، poppler-utils (`pdftoppm`، `pdftotext`).

## التصنيف التعريفي (من مصادر knowledge-base/)

```bash
python -m visite tarif 3506.99.90.00 --notes     # القسم، الفصل، البند، السطر، الحق الجمركي، الملاحظات، قانون المالية 2026، قرارات التصنيف
python -m visite tarif dossiers/X/dossier.json   # نفس البطاقة لكل مادة + مقارنة مع رمز بلد المنشأ
```

المراقبات الجديدة في `controler`:
- `TAR`: هل الرمز موجود في التعريفة؟
- `DD`: هل نسبة الحق الجمركي المصرّح بها مطابقة للتعريفة؟
- `FAM`: هل رمز بلد المنشأ من نفس العائلة (نفس SH6)؟

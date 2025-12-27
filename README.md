# EtqDebug - Production Reliance Debugger

EtqDebug is a **production-grade debugging utility** for EtQ Reliance Jython scripts. Rich hierarchical logging with automatic field substitution, prod/dev auto-config, caller context, and built-in DB/profiling utilities.

## 🚀 Features

- **Smart auto-config**: Debug in dev, error-only in prod (ADMIN override)
- **Rich caller info**: Function + line # + params (default ON)
- **Field substitution**: `{ETQ$NUMBER}` → `#00001`
- **5-level filtering**: debug/info/warn/error/none + aliases
- **Unicode-safe**: Jython 2.7 robust encoding
- **Document alerts**: `alert()` → `document.addWarning()`
- **DB schema inspector**: `databaseTableInfo("users")`
- **Profiler**: `@debug.profileThis` + `profileCode()`
- **Force override**: `enabled=True` bypasses filtering

## 🔍 Document Field Substitution

**Automatic `thisDocument` binding** - Fields resolve from current context:
```python
debug = EtqDebug() # Uses thisDocument automatically
debug.log("Doc #{ETQ$NUMBER} saved") # → "Doc #00001 saved"
```
**Instance-level override**:
```python
debug = EtqDebug(document=otherDocument) # Binds to specific PublicDocument
debug.log("Other doc: {CUSTOM_FIELD}") # Uses otherDocument fields
```

**Per-call override**:
```python
debug.log("Cross-doc: {FIELD_NAME}", document=someOtherDocument)
```

**How it works**:
1. `_getFieldsInString()` scans for `{FIELDNAME}` patterns
2. Calls `document.getField(FIELDNAME).getEncodedDisplayText()`
3. Supports link fields, text fields, single value dropdowns, etc.
4. Falls back gracefully: `{MISSING}` → `{MISSING}`

## ⚖️ Level-Based Filtering

**Hierarchical filtering** - only messages at/above minLevel emit:

| Level Order | Dev Default | Prod Default | Aliases | Index |
|-------------|-------------|--------------|---------|-------|
| `debug` (0) | ✅ | ADMIN only | `debug` | 0 |
| `info` (1)  | ✅ | ❌ | `info`, `information` | 1 |
| `warn` (2)  | ✅ | ❌ | `warn`, `warning` | 2 |
| `error` (3) | ✅ | ✅ | `error` | 3 |
| `none` (4)  | ❌ | ❌ | `none`, `off`, `disabled` | 4 |

**Logic**: `callerLevelIndex >= minLevelIndex`
```python
debug = EtqDebug(minLevel='warn') # Filters debug/info
debug.log("This shows", level='error') # ✅ Index 3 >= 2
debug.log("This hides", level='debug') # ❌ Index 0 < 2
debug.log("This forces", level='debug', enabled=True) # ✅ Force override
```
**Auto-detection**:
Dev environment → minLevel='debug' (all admins)
Production → minLevel='error' (unless ADMINISTRATORS group)
```python
env = engineConfig.getEnvironmentName()
isProd = env.lower() in ['production', 'prod']
```
## 📦 `log()` Method - Complete Reference

### Signature
```python
def log(self, msg, label=None, multiple=False, enabled=False, document=None, level='debug', showCaller=True)
```

text

### Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `msg` | any | required | Message, dict, list, or iterable |
| `label` | str | `None` | Message label (defaults to `"msg"`) |
| `multiple` | bool | `False` | Treat `msg` as iterable (dict/list), splits iterables on multiple lines with each element getting logged |
| `enabled` | bool | `False` | **Force log** (bypasses level filtering) |
| `document` | PublicDocument | `None` | **Override** field substitution document |
| `level` | str | `'debug'` | Log level (`debug`, `info`, `warn`, `error`) |
| `showCaller` | bool | `True` | Include line #/class/function/params |

## 🛠️ `log()` Examples
### 1. Simple Messages
```python
debug.log("User saved") # [msg: User saved]
debug.log("Status update", "Processing") # [Processing: Status update]
debug.log("Quick check", showCaller=False) # No caller info
```
text

**Output**:
```log
[DEBUG] VACATION1 - FORM #00001
MyForm.onSave() line=23:
    params: user='john.doe'
    Processing: Status update
```
text

### 2. Field Substitution
```python
debug.log("Doc #{ETQ$NUMBER} by {USERNAME}") # Auto thisDocument
debug.log("Check {STATUS} on #{ETQ$NUMBER}", document=relatedDoc)
```
**Output**:
```log
msg: Doc #00001 by john.doe
```

### 3. Structured Data (`multiple=True`)
```python
errors = [{"field": "NAME", "error": "Required"}, {"field": "DATE", "error": "Invalid"}]
debug.log(errors, "Validation Errors", multiple=True)
```

text

**Output**:
```log
[DEBUG] VACATION1 - FORM #00001
ValidationClass.validate() line=45:
    params: document=<PublicDocument>
    Validation Errors:
        0: {'field': 'NAME', 'error': 'Required'}
        1: {'field': 'DATE', 'error': 'Invalid'}
```

text

### 4. Nested Structures
```python
data = {
"user": "john.doe",
"errors": [{"field": "NAME"}, {"field": "EMAIL"}],
"stats": {"total": 5, "valid": 3}
}
debug.log(data, "Form Data", multiple=True)
```
text

**Output**:
```log
Form Data:
    user: john.doe
    errors:
        0: {'field': 'NAME'}
        1: {'field': 'EMAIL'}
    stats:
        total: 5
        valid: 3
```
## 📋 Quick Reference Table

| Use Case | Code | Output Style |
|----------|------|--------------|
| Simple msg | `debug.log("text")` | `msg: text` |
| Labeled | `debug.log("text", "Label")` | `Label: text` |
| Structured | `debug.log(data, "Data", multiple=True)` | Nested hierarchy |
| Force prod | `debug.log("text", enabled=True)` | Always shows |
| Cross-doc | `debug.log("text", document=doc)` | Uses doc fields |
| No caller | `debug.log("text", showCaller=False)` | Compact |

### 5. Production Force Logging
```python
debug = EtqDebug(minLevel='error') # Prod mode

debug.log("Debug info", level='debug') # ❌ Filtered
debug.log("Debug forced", level='debug', enabled=True) # ✅ Shows
debug.log("Error auto-shows", level='error') # ✅ Auto-shows
```

### 6. Level-Specific Examples
```python
debug.log("Debug details", level='debug')
debug.log("Info update", level='info')
debug.log("Warning issued", level='warn')
debug.log("CRITICAL ERROR", level='error')
```

## 📦 EtQScript Profile Setup

### 1. Create EtQScript Profile
1. Navigate to **Administration Center**
2. New Document → **EtQScript Profile**
3. **Paste the full EtqDebug class code** into the formula editor
4. **Name your profile** (e.g., `Debug`)

### 2. Import in Any Script - Shared Formulas Recommended
Replace 'YOUR_PROFILE_NAME' with your actual design name
```python
exec(publicEtQScriptProfilesManager.getScriptProfile('YOUR_PROFILE_NAME').getFormula())
```

text

### 3. Use Immediately
Now available globally in this script context
```python
debug = EtqDebug() # Auto prod/dev + document detection

debug.log("User saved") # Rich caller output
debug.log(errors, "Validation", multiple=True) # Nested data
debug.alert("Required field missing") # Document warning
```
text

**Sample output**:
```log
[DEBUG] VACATION1 - VACA1_TEST_VACATION_REQUEST #00001
TestClass.testMethod() line=17:
    params: document=<PublicDocument>, field='name'
    msg: User saved
```
text

## 🛠️ Usage Examples

### Basic Logging (After Import)
```python
exec(publicEtQScriptProfilesManager.getScriptProfile('DEBUG').getFormula())

debug = EtqDebug()
debug.log("Processing complete") # Default: showCaller=True
debug.log("Quick status", showCaller=False) # Compact
```
text

### Form Event / Workflow Script
Form: onOpen, onRefresh, onSave, Workflow, etc.
exec(publicEtQScriptProfilesManager.getScriptProfile('EtqDebug_Production').getFormula())
```python
debug = EtqDebug()
debug.log("Form saved: {ETQ$NUMBER}", enabled=True)
```
text

### Client-Specific Profiles
Profile Name: VacationDebug
Profile Name: InventoryDebug
Profile Name: HRDebug

text
undefined
Import client-specific
```python
exec(publicEtQScriptProfilesManager.getScriptProfile('VacationDebug').getFormula())
debug = VacationDebug() # Uses vacation-specific DB datasource
```
text

## ⚙️ Configuration

### Client Subclassing (Separate Profiles)
Create **separate EtQScript Profiles** for each client/app:

**Profile: `InventoryDebug`**
```python
class InventoryDebug(EtqDebug):
DEFAULT_FILTER_DATASOURCE = 'INVENTORY_DS'
DEFAULT_SCHEMA_NAME = 'warehouse'
```
Rest of EtqDebug class code...
text

**Usage**:
```python
exec(publicEtQScriptProfilesManager.getScriptProfile('InventoryDebug').getFormula())
debug = InventoryDebug() # Custom defaults applied
```
text

## 📋 Complete Import + Usage Template

===== ETQDEBUG TEMPLATE =====
```python
exec(publicEtQScriptProfilesManager.getScriptProfile('EtqDebug_Production').getFormula())

Your script logic here
debug = EtqDebug(label="MYFORM - {ETQ$NUMBER}")

try:
    # Your code...
    result = processData()
    debug.log("SUCCESS: {}".format(result), "Process")

except Exception as e:
    debug.log("ERROR: {}".format(str(e)), "Exception", level='error', enabled=True)
    raise
```

text

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **`NameError: EtqDebug`** | Check profile **design name** matches import |
| **No output** | Prod? Use `enabled=True` or check ADMINISTRATORS |
| **`publicEtQScriptProfilesManager` error** | Profile not published/activated |
| **Fields not working** | Pass `document=thisDocument` |

## ✨ Best Practices

✅ ONE import line → FULL debugging suite
✅ Create per-app profiles (VacationDebug, InventoryDebug)
✅ enabled=True for prod quick-tests
✅ multiple=True for dict/list data
✅ @debug.profileThis for slow functions

text

## 📂 Deployment Steps

1. **Create** → Administration Center → New Document → New EtQScript Profile
2. **Paste** → Full EtqDebug class code (this README + source)
3. **Name** → `EtqDebug_Production` (or client-specific)
4. **Publish** → Make active
5. **Import** → `exec(publicEtQScriptProfilesManager.getScriptProfile('YOUR_NAME').getFormula())`

## 🚀 Production Ready

**Zero dependencies** beyond standard Reliance APIs. Works in:
- Form events (`onOpen`, `onRefresh`, `onSave`, `Shared Formulas`)
- Workflow scripts
- Batch processes (Task Profiles)

TEST IT NOW
```python
exec(publicEtQScriptProfilesManager.getScriptProfile('EtqDebug_Production').getFormula())
debug = EtqDebug()
debug.log("README TEST - READY!", enabled=True)
```
text

**Copy → Paste → Debug → Repeat.** 🎉
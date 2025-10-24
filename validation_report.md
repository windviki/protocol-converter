# YAML Validation Report
==================================================
Generated at: 2025-10-24 17:40:13

## Summary
- Total files: 30
- Valid files: 17
- Invalid files: 13
- Total issues: 17
- Total errors: 7
- Total warnings: 4
- Success rate: 56.7%

## Detailed Results
### A-1.meta.yaml - ✅ Valid
- Processing time: 0.013s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-1.yaml - ✅ Valid
- Processing time: 0.002s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-2.meta.yaml - ✅ Valid
- Processing time: 0.016s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-2.yaml - ✅ Valid
- Processing time: 0.004s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-3.meta.yaml - ✅ Valid
- Processing time: 0.020s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-3.yaml - ❌ Invalid
- Processing time: 0.002s
- Issues: 1 (Errors: 1, Warnings: 0)
  Issues:
  ❌ Failed to parse YAML template: while parsing a flow node
expected the node content, but found '-'
  in "<unicode string>", line 5, column 1:
    - name: __JINJA_PLACEHOLDER_1__
    ^
     Path: protocols_yaml\A\A-3.yaml
     Suggestion: Check YAML syntax and Jinja2 expressions

### A-4.meta.yaml - ✅ Valid
- Processing time: 0.027s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-4.yaml - ✅ Valid
- Processing time: 0.003s
- Issues: 0 (Errors: 0, Warnings: 0)

### A-5.meta.yaml - ❌ Invalid
- Processing time: 0.030s
- Issues: 2 (Errors: 1, Warnings: 1)
  Issues:
  ❌ Mismatched Jinja2 variable brackets: 22 '{' vs 12 '}'
     Path: protocols_yaml\A\A-5.meta.yaml
     Suggestion: Check for missing or extra brackets in Jinja2 expressions
  ⚠️ Unclosed Jinja2 variable
     Path: protocols_yaml\A\A-5.meta.yaml
     Suggestion: Review and fix the Jinja2 syntax

### A-5.yaml - ❌ Invalid
- Processing time: 0.001s
- Issues: 1 (Errors: 1, Warnings: 0)
  Issues:
  ❌ Failed to parse YAML template: while parsing a flow node
expected the node content, but found '-'
  in "<unicode string>", line 7, column 3:
      - name: __JINJA_PLACEHOLDER_2__
      ^
     Path: protocols_yaml\A\A-5.yaml
     Suggestion: Check YAML syntax and Jinja2 expressions

### B-1.meta.yaml - ✅ Valid
- Processing time: 0.010s
- Issues: 0 (Errors: 0, Warnings: 0)

### B-1.yaml - ✅ Valid
- Processing time: 0.002s
- Issues: 0 (Errors: 0, Warnings: 0)

### B-2.meta.yaml - ✅ Valid
- Processing time: 0.009s
- Issues: 0 (Errors: 0, Warnings: 0)

### B-2.yaml - ✅ Valid
- Processing time: 0.003s
- Issues: 0 (Errors: 0, Warnings: 0)

### B-3.meta.yaml - ❌ Invalid
- Processing time: 0.015s
- Issues: 1 (Errors: 1, Warnings: 0)
  Issues:
  ❌ Mismatched Jinja2 variable brackets: 6 '{' vs 4 '}'
     Path: protocols_yaml\B\B-3.meta.yaml
     Suggestion: Check for missing or extra brackets in Jinja2 expressions

### B-3.yaml - ✅ Valid
- Processing time: 0.002s
- Issues: 0 (Errors: 0, Warnings: 0)

### B-4.meta.yaml - ❌ Invalid
- Processing time: 0.021s
- Issues: 2 (Errors: 1, Warnings: 1)
  Issues:
  ❌ Mismatched Jinja2 variable brackets: 25 '{' vs 13 '}'
     Path: protocols_yaml\B\B-4.meta.yaml
     Suggestion: Check for missing or extra brackets in Jinja2 expressions
  ⚠️ Unclosed Jinja2 variable
     Path: protocols_yaml\B\B-4.meta.yaml
     Suggestion: Review and fix the Jinja2 syntax

### B-4.yaml - ✅ Valid
- Processing time: 0.008s
- Issues: 0 (Errors: 0, Warnings: 0)

### B-5.meta.yaml - ❌ Invalid
- Processing time: 0.001s
- Issues: 1 (Errors: 0, Warnings: 0)
  Issues:
  ❌ Validation failed: too many values to unpack (expected 2)
     Path: protocols_yaml\B\B-5.meta.yaml

### B-5.yaml - ❌ Invalid
- Processing time: 0.000s
- Issues: 1 (Errors: 0, Warnings: 0)
  Issues:
  ❌ Validation failed: too many values to unpack (expected 2)
     Path: protocols_yaml\B\B-5.yaml

### C-1.meta.yaml - ✅ Valid
- Processing time: 0.012s
- Issues: 0 (Errors: 0, Warnings: 0)

### C-1.yaml - ✅ Valid
- Processing time: 0.002s
- Issues: 0 (Errors: 0, Warnings: 0)

### C-2.meta.yaml - ✅ Valid
- Processing time: 0.012s
- Issues: 0 (Errors: 0, Warnings: 0)

### C-2.yaml - ✅ Valid
- Processing time: 0.003s
- Issues: 0 (Errors: 0, Warnings: 0)

### C-3.meta.yaml - ❌ Invalid
- Processing time: 0.002s
- Issues: 1 (Errors: 0, Warnings: 0)
  Issues:
  ❌ Validation failed: too many values to unpack (expected 2)
     Path: protocols_yaml\C\C-3.meta.yaml

### C-3.yaml - ❌ Invalid
- Processing time: 0.001s
- Issues: 1 (Errors: 0, Warnings: 0)
  Issues:
  ❌ Validation failed: too many values to unpack (expected 2)
     Path: protocols_yaml\C\C-3.yaml

### C-4.meta.yaml - ❌ Invalid
- Processing time: 0.025s
- Issues: 2 (Errors: 1, Warnings: 1)
  Issues:
  ❌ Mismatched Jinja2 variable brackets: 48 '{' vs 36 '}'
     Path: protocols_yaml\C\C-4.meta.yaml
     Suggestion: Check for missing or extra brackets in Jinja2 expressions
  ⚠️ Unclosed Jinja2 variable
     Path: protocols_yaml\C\C-4.meta.yaml
     Suggestion: Review and fix the Jinja2 syntax

### C-4.yaml - ❌ Invalid
- Processing time: 0.001s
- Issues: 1 (Errors: 0, Warnings: 0)
  Issues:
  ❌ Validation failed: too many values to unpack (expected 2)
     Path: protocols_yaml\C\C-4.yaml

### C-5.meta.yaml - ❌ Invalid
- Processing time: 0.081s
- Issues: 2 (Errors: 1, Warnings: 1)
  Issues:
  ❌ Mismatched Jinja2 variable brackets: 166 '{' vs 92 '}'
     Path: protocols_yaml\C\C-5.meta.yaml
     Suggestion: Check for missing or extra brackets in Jinja2 expressions
  ⚠️ Unclosed Jinja2 variable
     Path: protocols_yaml\C\C-5.meta.yaml
     Suggestion: Review and fix the Jinja2 syntax

### C-5.yaml - ❌ Invalid
- Processing time: 0.002s
- Issues: 1 (Errors: 0, Warnings: 0)
  Issues:
  ❌ Validation failed: too many values to unpack (expected 2)
     Path: protocols_yaml\C\C-5.yaml

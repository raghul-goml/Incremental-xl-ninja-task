import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# Initialize workbook
wb = openpyxl.Workbook()

# Setup sheets
ws_summary = wb.active
ws_summary.title = "Overview & Scope"
ws_reg = wb.create_sheet(title="User Registration")
ws_cat = wb.create_sheet(title="Catalog & Browsing")

# Professional Corporate Palette
font_title = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
font_section = Font(name="Calibri", size=12, bold=True, color="1F497D")
font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
font_body = Font(name="Calibri", size=10, color="000000")
font_bold = Font(name="Calibri", size=10, bold=True, color="000000")

fill_navy_title = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
fill_navy_header = PatternFill(start_color="244062", end_color="244062", fill_type="solid")
fill_light_blue = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
fill_zebra = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")
fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

thin_border_side = Side(border_style="thin", color="D9D9D9")
thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
header_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=Side(border_style="medium", color="1F497D"))

align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
align_header = Alignment(horizontal="center", vertical="center", wrap_text=True)

# -----------------------------
# Sheet 1: Overview & Scope
# -----------------------------
ws_summary.views.sheetView[0].showGridLines = True
ws_summary.merge_cells("A1:E2")
title_cell = ws_summary["A1"]
title_cell.value = "Sauce Demo (Shopify) - QA Test & Functional Specification"
title_cell.font = font_title
title_cell.fill = fill_navy_title
title_cell.alignment = align_center

summary_info = [
    ("Target Application URL", "https://sauce-demo.myshopify.com/"),
    ("Platform Architecture", "Shopify Storefront with Social Shopping App integrations (Sauce)"),
    ("Document Type", "Functional Specification & Test Case Matrix"),
    ("Author / QA Lead", "QA Automation & Testing Team"),
    ("Version / Baseline", "1.0 - Storefront Core Verification"),
]

row = 4
for label, val in summary_info:
    ws_summary.cell(row=row, column=1, value=label).font = font_bold
    ws_summary.cell(row=row, column=1).fill = fill_light_blue
    ws_summary.cell(row=row, column=1).border = thin_border
    ws_summary.merge_cells(start_row=row, start_column=2, end_row=row, end_column=5)
    data_cell = ws_summary.cell(row=row, column=2, value=val)
    data_cell.font = font_body
    for col_idx in range(2, 6):
        ws_summary.cell(row=row, column=col_idx).border = thin_border
    row += 1

row += 2
ws_summary.cell(row=row, column=1, value="Modules in Scope").font = font_section
row += 1

scope_headers = ["Module ID", "Module Name", "Primary Route / Path", "Key Capabilities & Coverage", "Total Test Cases"]
for col_idx, h in enumerate(scope_headers, 1):
    c = ws_summary.cell(row=row, column=col_idx, value=h)
    c.font = font_header
    c.fill = fill_navy_header
    c.alignment = align_header
    c.border = header_border

modules = [
    ("MOD-01", "User Registration", "/account/register", "Account creation, mandatory field validations, email syntax, duplicates, session persistence", 5),
    ("MOD-02", "Catalog & Product Browsing", "/collections/all & /products/*", "Product grid display, pricing & currency (GBP £), PDP details, quantity selectors, mini-cart sync", 5),
]

row += 1
for m in modules:
    for col_idx, val in enumerate(m, 1):
        c = ws_summary.cell(row=row, column=col_idx, value=val)
        c.font = font_body
        c.border = thin_border
        c.alignment = align_center if col_idx in [1, 5] else align_left
    row += 1

ws_summary.column_dimensions["A"].width = 18
ws_summary.column_dimensions["B"].width = 28
ws_summary.column_dimensions["C"].width = 26
ws_summary.column_dimensions["D"].width = 50
ws_summary.column_dimensions["E"].width = 16

# -----------------------------
# Reusable Sheet Formatter
# -----------------------------
def format_test_sheet(ws, module_title, module_route, test_cases):
    ws.views.sheetView[0].showGridLines = True
    
    ws.merge_cells("A1:H2")
    t_cell = ws["A1"]
    t_cell.value = f"Test Cases: {module_title}"
    t_cell.font = font_title
    t_cell.fill = fill_navy_title
    t_cell.alignment = align_center
    
    ws.cell(row=3, column=1, value="Module Route:").font = font_bold
    ws.cell(row=3, column=1).fill = fill_light_blue
    ws.cell(row=3, column=1).border = thin_border
    ws.merge_cells("B3:D3")
    ws.cell(row=3, column=2, value=module_route).font = font_body
    for col in range(2, 5):
        ws.cell(row=3, column=col).border = thin_border
        
    ws.cell(row=3, column=5, value="Execution Environment:").font = font_bold
    ws.cell(row=3, column=5).fill = fill_light_blue
    ws.cell(row=3, column=5).border = thin_border
    ws.merge_cells("F3:H3")
    ws.cell(row=3, column=6, value="Chrome / Firefox / Mobile Safari (Webkit)").font = font_body
    for col in range(6, 9):
        ws.cell(row=3, column=col).border = thin_border
        
    headers = [
        "Test ID", "Test Scenario", "Severity", "Pre-conditions", 
        "Test Steps / Action", "Input Test Data", "Expected Result", "Status"
    ]
    
    start_row = 5
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=start_row, column=col_idx, value=h)
        c.font = font_header
        c.fill = fill_navy_header
        c.alignment = align_header
        c.border = header_border
        
    curr_row = start_row + 1
    for idx, tc in enumerate(test_cases):
        fill = fill_zebra if idx % 2 == 0 else fill_white
        for col_idx, val in enumerate(tc, 1):
            c = ws.cell(row=curr_row, column=col_idx, value=val)
            c.font = font_body
            c.border = thin_border
            c.fill = fill
            c.alignment = align_center if col_idx in [1, 3, 8] else align_left
        ws.row_dimensions[curr_row].height = 42
        curr_row += 1

    col_widths = {"A": 12, "B": 26, "C": 12, "D": 22, "E": 34, "F": 22, "G": 34, "H": 14}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

# -----------------------------
# Data Sets
# -----------------------------
reg_cases = [
    ["REG-001", "Successful Account Creation", "Critical", "User is unauthenticated", "1. Navigate to /account/register\n2. Populate valid inputs\n3. Click 'Create'", "FN: Jane\nLN: Doe\nEmail: jane.test{ts}@example.com\nPW: Password123!", "Account created. User redirected to /account dashboard with active session.", "Ready"],
    ["REG-002", "Blank Mandatory Field Submission", "High", "User is on /account/register", "1. Leave Email and Password empty\n2. Click 'Create'", "Email: [Empty]\nPassword: [Empty]", "Form submission prevented; displays standard Shopify blank field error.", "Ready"],
    ["REG-003", "Malformed Email Syntax", "Medium", "User is on /account/register", "1. Enter email missing @ or domain\n2. Click 'Create'", "Email: invaliduser@test\nPW: ValidPass123", "Validation flags invalid email format and halts submission.", "Ready"],
    ["REG-004", "Duplicate Account Registration", "High", "Account already exists", "1. Enter existing email\n2. Fill password and click 'Create'", "Email: existing_user@example.com\nPW: ValidPass123", "Displays: 'This email address is already associated with an account.'", "Ready"],
    ["REG-005", "Password Minimum Length Check", "Medium", "User is on /account/register", "1. Enter password < 5 characters\n2. Submit form", "Email: unique@example.com\nPW: 1234", "Validation triggers error requiring minimum character threshold.", "Ready"]
]

cat_cases = [
    ["CAT-001", "Catalog Inventory & Grid Verification", "Critical", "Store has active products", "1. Open main menu\n2. Click 'Catalog' link (/collections/all)\n3. Inspect cards", "Target items:\n- Grey jacket (£55.00)\n- Noir jacket (£60.00)\n- Striped top (£50.00)", "All products render with thumbnail, title, and formatted GBP (£) pricing.", "Ready"],
    ["CAT-002", "Product Detail Page (PDP) Navigation", "Critical", "User is browsing /collections/all", "1. Click on 'Noir jacket' card\n2. Check URL, title, media, CTA", "Item: Noir jacket\nSlug: /products/noir-jacket", "Navigates to PDP. Shows high-res images, description, £60.00 price, and CTA.", "Ready"],
    ["CAT-003", "Price & Currency Consistency", "High", "Storefront loaded", "1. Note catalog card price\n2. Open PDP and compare price", "Grey jacket: £55.00\nNoir jacket: £60.00", "Prices match exactly in British Pounds (£) without decimal rounding issues.", "Ready"],
    ["CAT-004", "Quantity Selector & Mini-Cart Sync", "High", "User is on any PDP", "1. Set quantity to 3\n2. Click 'Add to Cart'\n3. Observe header cart widget", "Quantity: 3\nItem: Striped top (£50.00)", "Mini-cart counter updates to 'My Cart (3)'. Preview reflects £150.00 subtotal.", "Ready"],
    ["CAT-005", "Responsive Catalog Reflow", "Medium", "Browser set to 375px viewport", "1. Access /collections/all on mobile\n2. Inspect grid and menu", "Desktop: 1440px\nMobile: 375px", "Grid reflows cleanly to mobile layout without clipping or broken touch targets.", "Ready"]
]

format_test_sheet(ws_reg, "Module: User Registration", "/account/register", reg_cases)
format_test_sheet(ws_cat, "Module: Catalog & Product Browsing", "/collections/all & /products/*", cat_cases)

wb.save("Sauce_Demo_Shopify_QA_Specification.xlsx")
"""Generate per-team food preorder tickets (one page per order) from the
Google Forms "Food Pre-Order" responses CSV.

Run from scripts/: python generate_food_preorders.py [responses.csv]
If no path is given, a tkinter file dialog asks for the CSV (opened in
database/CSV_Imports/, gitignored - the responses contain contact info,
never commit them).

Writes one HTML + PDF ticket per order and an all_food_orders.pdf print
file into generated_food_orders/ (both extensions are gitignored).
Tickets list item x quantity only, no prices.
"""
import csv
import os
import re
import sys
from html import escape

from weasyprint import HTML

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, os.path.join(REPO_DIR, "database"))
from file_picker import pick_csv  # noqa: E402

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "generated_food_orders")
HTML_DIR = os.path.join(OUTPUT_DIR, "HTML")

# Every non-item column in the responses sheet; the rest are food items.
META_COLUMNS = {
    "Timestamp",
    "Email Address",
    "Team Name",
    "Team Number",
    "Contact Person Name",
    "Contact Person Email",
    "Contact Person #Cell",
    "Total Price",
    "Generated Email",
    "Email Sent",
}

STYLES = """
    @page { size: letter; margin: 0.6in; }
    body { font-family: sans-serif; }
    .ticket { break-after: page; }
    .ticket:last-child { break-after: auto; }
    h1 { margin: 0 0 4px; }
    .subtitle { font-size: 20px; margin: 0 0 4px; }
    .contact { font-size: 14px; color: #555; margin: 0 0 16px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid black; padding: 8px; text-align: left; }
    th { background-color: #f2f2f2; }
    td.qty { text-align: center; width: 1.2in; font-size: 18px; font-weight: bold; }
"""


def item_label(column):
    """'Large Cheese Pizza ($24.00)' -> 'Large Cheese Pizza'."""
    return re.sub(r"\s*\(\$[^)]*\)\s*$", "", column).strip()


def quantity(value):
    value = (value or "").strip()
    return int(value) if value.isdigit() else 0


def slugify(value):
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_") or "order"


def ticket_page(row, item_columns):
    items = [(item_label(col), quantity(row.get(col))) for col in item_columns]
    items = [(name, qty) for name, qty in items if qty > 0]
    rows = "".join(f"""
        <tr>
            <td>{escape(name)}</td>
            <td class="qty">{qty}</td>
        </tr>""" for name, qty in items)
    table = f"""
    <table>
        <tr>
            <th>Item</th>
            <th>Quantity</th>
        </tr>{rows}
    </table>""" if items else "<p>No items ordered.</p>"
    contact = " | ".join(part for part in (
        row.get("Contact Person Name", "").strip(),
        row.get("Contact Person Email", "").strip(),
    ) if part)
    return f"""
<div class="ticket">
    <h1>{escape(row.get("Team Name", "").strip() or "Unknown Team")}</h1>
    <div class="subtitle">Team Number: <strong>{escape(row.get("Team Number", "").strip() or "?")}</strong></div>
    <div class="contact">{escape(contact)}</div>
    {table}
</div>
"""


def html_document(title, body):
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{escape(title)}</title>
    <style>{STYLES}</style>
</head>
<body>
{body}
</body>
</html>
"""


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else pick_csv(
        "Select the food preorder responses CSV",
        initialdir=os.path.join(REPO_DIR, "database", "CSV_Imports"),
    )
    if not csv_path:
        raise SystemExit("No CSV selected")

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        item_columns = [c for c in reader.fieldnames if c not in META_COLUMNS]
        orders = [row for row in reader if (row.get("Team Name") or "").strip()]
    orders.sort(key=lambda row: row["Team Name"].strip().lower())
    print(f"{len(orders)} orders, {len(item_columns)} menu items")

    os.makedirs(HTML_DIR, exist_ok=True)
    documents = []
    for row in orders:
        team_name = row["Team Name"].strip()
        slug = slugify(row.get("Team Number", "").strip() or team_name)
        page = ticket_page(row, item_columns)
        ticket_html = html_document(f"Food Order - {team_name}", page)

        html_path = os.path.join(HTML_DIR, f"food_order_{slug}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(ticket_html)

        pdf_path = os.path.join(OUTPUT_DIR, f"food_order_{slug}.pdf")
        document = HTML(string=ticket_html).render()
        document.write_pdf(pdf_path)
        documents.append(document)
        print(f"Food order ticket generated: {pdf_path}")

    if documents:
        pages = [page for document in documents for page in document.pages]
        combined_path = os.path.join(OUTPUT_DIR, "all_food_orders.pdf")
        documents[0].copy(pages).write_pdf(combined_path)
        print(f"Combined food orders PDF generated: {combined_path} ({len(pages)} pages)")
    else:
        print("No orders found; combined PDF not generated.")


if __name__ == "__main__":
    main()

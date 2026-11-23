
from io import BytesIO
from decimal import Decimal

from django.db.models import Sum

from accounts.models import Payment

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ==================================================
# GENERATE PAYMENT RECEIPT PDF
# ==================================================

def generate_payment_receipt(payment):

    # Create PDF in memory
    buffer = BytesIO()

    # Configure PDF page
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # Load default styles
    styles = getSampleStyleSheet()

    # Shop heading style
    shop_style = ParagraphStyle(
        "ShopHeading",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        textColor=colors.HexColor("#172554"),
        spaceAfter=5,
    )

    # Receipt subtitle style
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=15,
    )

    # Section heading style
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#172554"),
        spaceBefore=12,
        spaceAfter=8,
    )

    # Store PDF elements
    story = []

    # Get shop details
    shop = payment.shop

    # Shop name
    story.append(
        Paragraph(
            shop.name,
            shop_style
        )
    )

    # Shop address
    if shop.address:
        story.append(
            Paragraph(
                shop.address,
                subtitle_style
            )
        )

    # Receipt title
    story.append(
        Paragraph(
            "PAYMENT RECEIPT",
            subtitle_style
        )
    )

    story.append(Spacer(1, 10))

    # Get customer details
    customer = payment.loan.customer

    # Customer and loan section
    story.append(
        Paragraph(
            "CUSTOMER & LOAN DETAILS",
            section_style
        )
    )

    details = [
        ["Receipt Number", payment.receipt_number],
        ["Loan Number", payment.loan.loan_number],
        ["Customer Name", customer.full_name],
        ["Customer Phone", customer.phone_number or "-"],
        [
            "Payment Date",
            payment.payment_date.strftime("%d-%m-%Y")
        ],
    ]

    details_table = Table(
        details,
        colWidths=[55 * mm, 100 * mm]
    )

    details_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#EFF6FF")
            ),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )

    story.append(details_table)

    # Payment breakdown section
    story.append(
        Paragraph(
            "PAYMENT BREAKDOWN",
            section_style
        )
    )

    payment_details = [
        ["Description", "Amount (INR)"],
        [
            "Interest Paid",
            f"Rs. {payment.interest_amount:,.2f}"
        ],
        [
            "Principal Paid",
            f"Rs. {payment.principal_amount:,.2f}"
        ],
        [
            "TOTAL PAID",
            f"Rs. {payment.amount:,.2f}"
        ],
    ]

    payment_table = Table(
        payment_details,
        colWidths=[95 * mm, 60 * mm]
    )

    payment_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#172554")
            ),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 9),
            (
                "BACKGROUND",
                (0, -1),
                (-1, -1),
                colors.HexColor("#DBEAFE")
            ),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ])
    )

    story.append(payment_table)

    # ----------------------------------------------
    # REMAINING PRINCIPAL ON THIS RECEIPT DATE
    # ----------------------------------------------

    result = Payment.objects.filter(
        loan=payment.loan,
        payment_date__lte=payment.payment_date
    ).aggregate(
        total_paid=Sum("principal_amount")
    )

    # Get total principal paid up to receipt date
    total_principal_paid = (
        result["total_paid"] or Decimal("0.00")
    )

    # Calculate remaining principal
    remaining_principal = (
        payment.loan.principal_amount - total_principal_paid
    )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            (
                "<b>Remaining Principal: "
                f"Rs. {remaining_principal:,.2f}</b>"
            ),
            styles["Heading2"]
        )
    )

    # Payment notes
    if payment.notes:

        story.append(Spacer(1, 10))

        story.append(
            Paragraph(
                f"Notes: {payment.notes}",
                styles["Normal"]
            )
        )

    # Owner signature section
    story.append(Spacer(1, 45))

    signature_table = Table(
        [
            ["", "________________________"],
            ["", "Owner Signature"],
        ],
        colWidths=[85 * mm, 70 * mm]
    )

    signature_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ])
    )

    story.append(signature_table)

    # Build PDF document
    document.build(story)

    # Move buffer pointer to beginning
    buffer.seek(0)

    return buffer

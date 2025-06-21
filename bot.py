import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
from telegram.constants import ChatAction
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Business Details
BUSINESS_NAME = "PRINCESS COLLECTION"
FROM_ADDRESS = """Princess Collection,
plot no :118,
sv nagar,perumalpattu,
thiruvallur-602024"""

# Conversation States
ASK_PRODUCT_COUNT, ASK_PRODUCT_NAME, ASK_ADDRESS, ASK_AMOUNT, ASK_SHIPPING = range(5)
user_data_dict = {
    "product_list": [],
    "product_count": 0,
    "current_product": 0,
}

# Logging
logging.basicConfig(level=logging.INFO)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Vanakkam! Welcome to Princess Collection Bot.\nHow many products are you ordering?")
    return ASK_PRODUCT_COUNT

# Ask how many products
async def ask_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.message.text)
        if count <= 0:
            raise ValueError
        user_data_dict['product_count'] = count
        user_data_dict['product_list'] = []
        user_data_dict['current_product'] = 0
        await update.message.reply_text(f"Enter name for Product 1:")
        return ASK_PRODUCT_NAME
    except ValueError:
        await update.message.reply_text("Please enter a valid number greater than 0.")
        return ASK_PRODUCT_COUNT

# Keep asking for all product names
async def collect_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_dict['product_list'].append(update.message.text)
    user_data_dict['current_product'] += 1

    if user_data_dict['current_product'] < user_data_dict['product_count']:
        await update.message.reply_text(f"Enter name for Product {user_data_dict['current_product'] + 1}:")
        return ASK_PRODUCT_NAME
    else:
        await update.message.reply_text("Please enter your delivery address:")
        return ASK_ADDRESS

# Ask amount
async def ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_dict['address'] = update.message.text
    await update.message.reply_text("Enter the product total amount (in Rs.):")
    return ASK_AMOUNT

# Ask shipping
async def ask_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_dict['amount'] = update.message.text
    await update.message.reply_text("Enter the shipping fee (in Rs.):")
    return ASK_SHIPPING

# Generate and send PDF
async def generate_bill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_dict['shipping'] = update.message.text
    total = float(user_data_dict['amount']) + float(user_data_dict['shipping'])

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)

    file_name = f"bill_{update.effective_user.id}.pdf"
    file_path = os.path.join(os.getcwd(), file_name)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, height - 80, "Princess Collection")

    # Logo
    try:
        logo = ImageReader("logo.png")
        c.drawImage(logo, width - 150, height - 120, width=80, height=80, mask='auto')
    except:
        c.setFillColor(colors.red)
        c.setFont("Helvetica", 10)
        c.drawString(width - 160, height - 100, "[Logo Missing]")

    # From Address
    y = height - 140
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(width - 180, y, "From:")
    for line in FROM_ADDRESS.split('\n'):
        y -= 15
        c.drawString(width - 180, y, line)

    # To Address
    y -= 50
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkgreen)
    c.drawString(50, y, "To Address:")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y -= 20
    for line in user_data_dict['address'].split('\n'):
        c.drawString(70, y, line)
        y -= 15

    # Product List
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkblue)
    c.drawString(50, y, "Product Names:")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    for i, product in enumerate(user_data_dict['product_list'], 1):
        y -= 18
        c.drawString(70, y, f"{i}. {product}")

    # Amounts
    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.brown)
    c.drawString(50, y, f"Product Amount: Rs. {user_data_dict['amount']}")
    y -= 25
    c.drawString(50, y, f"Shipping Fee: Rs. {user_data_dict['shipping']}")
    y -= 25
    c.setFillColor(colors.green)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Grand Total: Rs. {total}")

    # Footer
    y -= 50
    c.setFillColor(colors.grey)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(50, y, "Thank you for shopping with Princess Collection!")

    c.save()

    await update.message.reply_document(document=open(file_path, 'rb'), filename=file_name)
    os.remove(file_path)
    user_data_dict.clear()
    return ConversationHandler.END

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Order cancelled. Start again anytime.")
    user_data_dict.clear()
    return ConversationHandler.END

# Main
def main():
    app = ApplicationBuilder().token(os.getenv("7892449471:AAG_pBNvlyiReF2CGdAn9pWlUm3Abs9458M")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PRODUCT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_product_name)],
            ASK_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_products)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_amount)],
            ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_shipping)],
            ASK_SHIPPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_bill)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

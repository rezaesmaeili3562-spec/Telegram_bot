from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import json
from datetime import datetime, timedelta
import os
import re
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Tuple
import csv
from collections import defaultdict
import random

# 🔐 Token robot
TOKEN = "توکنی که از تلگرام گرفته اید رو اینجا وارد کنید"

# 📁 Database files
EXPENSES_FILE = "expenses.json"
USERS_FILE = "users.json"
BUDGETS_FILE = "budgets.json"
INCOMES_FILE = "incomes.json"
CATEGORIES_FILE = "categories.json"
BACKUP_FILE = "backup.json"

# Load data
def load_data(filename, default=None):
    if default is None:
        default = {} if not filename.endswith('.json') else []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== 🎨 Keyboard System ==========
class KeyboardManager:
    
    @staticmethod
    def get_main_keyboard():
        """Main bottom keyboard (always visible)"""
        keyboard = [
            [KeyboardButton("➕ هزینه جدید"), KeyboardButton("💰 درآمد جدید")],
            [KeyboardButton("📊 گزارش‌ها"), KeyboardButton("🎯 بودجه‌ها")],
            [KeyboardButton("📋 سرویس‌ها"), KeyboardButton("🔄 مدیریت")],
            [KeyboardButton("📈 آمار"), KeyboardButton("⚡ سریع")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def get_quick_keyboard():
        """Quick actions keyboard"""
        keyboard = [
            [KeyboardButton("🍔 غذا"), KeyboardButton("🚕 حمل‌ونقل")],
            [KeyboardButton("🛒 خرید"), KeyboardButton("🏠 خانه")],
            [KeyboardButton("💊 سلامت"), KeyboardButton("🎬 تفریح")],
            [KeyboardButton("🔙 بازگشت"), KeyboardButton("📝 توضیح")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def get_back_keyboard():
        """Back button keyboard"""
        keyboard = [[KeyboardButton("🔙 بازگشت"), KeyboardButton("🏠 منوی اصلی")]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def get_cancel_keyboard():
        """Cancel button keyboard"""
        keyboard = [[KeyboardButton("❌ لغو"), KeyboardButton("🏠 منوی اصلی")]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def get_management_keyboard():
        """Management keyboard"""
        keyboard = [
            [KeyboardButton("📤 خروجی"), KeyboardButton("📁 پشتیبان")],
            [KeyboardButton("⚙️ تنظیمات"), KeyboardButton("📋 دسته‌بندی")],
            [KeyboardButton("🔙 بازگشت"), KeyboardButton("🏠 منوی اصلی")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

class DropdownMenu:
    
    @staticmethod
    def categories_menu(selected=None) -> InlineKeyboardMarkup:
        """Categories dropdown menu"""
        categories = [
            ["🍔 غذا و رستوران", "food"],
            ["🚕 حمل و نقل", "transport"],
            ["🛒 خرید روزانه", "shopping"],
            ["🏠 خانه و قبوض", "house"],
            ["💊 سلامت و درمان", "health"],
            ["🎬 تفریح و سرگرمی", "entertainment"],
            ["📚 آموزش و کتاب", "education"],
            ["👕 پوشاک و مد", "clothing"],
            ["💻 فناوری و اینترنت", "tech"],
            ["🎁 هدیه و مناسبت", "gift"],
            ["✈️ سفر و گردش", "travel"],
            ["🚬 سیگار و دخانیات", "smoking"],
            ["🐕 حیوانات خانگی", "pets"],
            ["🎪 مهمانی و مراسم", "party"],
            ["📱 شارژ و اینترنت", "mobile"]
        ]
        
        keyboard = []
        row = []
        for i, (text, callback) in enumerate(categories, 1):
            row.append(InlineKeyboardButton(text, callback_data=f"cat_{callback}"))
            if i % 2 == 0 or i == len(categories):
                keyboard.append(row)
                row = []
        
        keyboard.append([InlineKeyboardButton("➕ دسته جدید", callback_data="cat_new")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def amounts_menu() -> InlineKeyboardMarkup:
        """Quick amounts dropdown menu"""
        amounts = [
            ["۱,۰۰۰ تومان", "1000"],
            ["۵,۰۰۰ تومان", "5000"],
            ["۱۰,۰۰۰ تومان", "10000"],
            ["۲۰,۰۰۰ تومان", "20000"],
            ["۵۰,۰۰۰ تومان", "50000"],
            ["۱۰۰,۰۰۰ تومان", "100000"],
            ["۲۰۰,۰۰۰ تومان", "200000"],
            ["۵۰۰,۰۰۰ تومان", "500000"],
            ["۱,۰۰۰,۰۰۰ تومان", "1000000"]
        ]
        
        keyboard = []
        row = []
        for i, (text, amount) in enumerate(amounts, 1):
            row.append(InlineKeyboardButton(text, callback_data=f"amount_{amount}"))
            if i % 3 == 0 or i == len(amounts):
                keyboard.append(row)
                row = []
        
        keyboard.append([InlineKeyboardButton("✍️ وارد کردن مبلغ دلخواه", callback_data="amount_custom")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_add")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def reports_menu() -> InlineKeyboardMarkup:
        """Reports dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("📅 امروز", callback_data="report_today"),
             InlineKeyboardButton("📆 این هفته", callback_data="report_week")],
            [InlineKeyboardButton("📊 این ماه", callback_data="report_month"),
             InlineKeyboardButton("📈 سه ماهه", callback_data="report_quarter")],
            [InlineKeyboardButton("📋 امسال", callback_data="report_year"),
             InlineKeyboardButton("📅 ماه قبل", callback_data="report_last_month")],
            [InlineKeyboardButton("📊 نمودار دایره‌ای", callback_data="chart_pie")],
            [InlineKeyboardButton("📈 نمودار میله‌ای", callback_data="chart_bar")],
            [InlineKeyboardButton("🔍 جستجوی پیشرفته", callback_data="search_advanced")],
            [InlineKeyboardButton("📤 خروجی اکسل", callback_data="export_excel"),
             InlineKeyboardButton("📄 خروجی PDF", callback_data="export_pdf")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def budgets_menu() -> InlineKeyboardMarkup:
        """Budget management dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("➕ ایجاد بودجه جدید", callback_data="budget_create")],
            [InlineKeyboardButton("📊 مشاهده بودجه‌ها", callback_data="budget_view")],
            [InlineKeyboardButton("✏️ ویرایش بودجه", callback_data="budget_edit")],
            [InlineKeyboardButton("🗑️ حذف بودجه", callback_data="budget_delete")],
            [InlineKeyboardButton("🔔 تنظیم هشدارها", callback_data="budget_alerts")],
            [InlineKeyboardButton("📊 مقایسه با ماه قبل", callback_data="budget_compare")],
            [InlineKeyboardButton("🎯 پیشنهاد بودجه هوشمند", callback_data="budget_smart")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def management_menu() -> InlineKeyboardMarkup:
        """Management dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("📤 خروجی داده‌ها", callback_data="export_data")],
            [InlineKeyboardButton("📁 پشتیبان‌گیری", callback_data="backup_create")],
            [InlineKeyboardButton("🔄 بازیابی پشتیبان", callback_data="backup_restore")],
            [InlineKeyboardButton("⚙️ تنظیمات ربات", callback_data="settings")],
            [InlineKeyboardButton("📋 مدیریت دسته‌بندی‌ها", callback_data="manage_categories")],
            [InlineKeyboardButton("🗑️ پاکسازی داده‌ها", callback_data="clean_data")],
            [InlineKeyboardButton("📊 آمار سیستم", callback_data="system_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def stats_menu() -> InlineKeyboardMarkup:
        """Statistics dropdown menu"""
        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data="stats_overview")],
            [InlineKeyboardButton("📈 روند ماهانه", callback_data="stats_monthly")],
            [InlineKeyboardButton("💰 گران‌ترین هزینه‌ها", callback_data="stats_top")],
            [InlineKeyboardButton("🏷️ هزینه بر اساس دسته", callback_data="stats_by_category")],
            [InlineKeyboardButton("📅 شلوغ‌ترین روزها", callback_data="stats_busy_days")],
            [InlineKeyboardButton("🎯 پیش‌بینی ماه آینده", callback_data="stats_forecast")],
            [InlineKeyboardButton("📊 مقایسه با میانگین", callback_data="stats_comparison")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_menu() -> InlineKeyboardMarkup:
        """Confirm/cancel dropdown menu"""
        keyboard = [
            [
                InlineKeyboardButton("✅ تایید", callback_data="confirm_yes"),
                InlineKeyboardButton("❌ لغو", callback_data="confirm_no")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def export_menu() -> InlineKeyboardMarkup:
        """Export options menu"""
        keyboard = [
            [InlineKeyboardButton("📊 Excel (.xlsx)", callback_data="export_excel_full")],
            [InlineKeyboardButton("📄 PDF گزارش", callback_data="export_pdf_report")],
            [InlineKeyboardButton("📝 CSV ساده", callback_data="export_csv")],
            [InlineKeyboardButton("📊 JSON کامل", callback_data="export_json")],
            [InlineKeyboardButton("📱 خروجی تلگرام", callback_data="export_telegram")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_management")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Settings menu"""
        keyboard = [
            [InlineKeyboardButton("🔔 هشدارها", callback_data="setting_alerts")],
            [InlineKeyboardButton("🎨 تم رنگی", callback_data="setting_theme")],
            [InlineKeyboardButton("💬 زبان ربات", callback_data="setting_language")],
            [InlineKeyboardButton("💰 واحد پول", callback_data="setting_currency")],
            [InlineKeyboardButton("📅 فرمت تاریخ", callback_data="setting_date")],
            [InlineKeyboardButton("🔄 یادآوری خودکار", callback_data="setting_reminder")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_management")]
        ]
        return InlineKeyboardMarkup(keyboard)

keyboard_manager = KeyboardManager()
menu = DropdownMenu()

# ========== 📊 Advanced Expense Management ==========
class AdvancedExpenseManager:
    
    @staticmethod
    def add_expense(user_id: str, amount: int, category: str, description: str = "", tags: List[str] = None) -> Dict:
        """Add new expense with advanced features"""
        expense = {
            "id": str(datetime.now().timestamp()),
            "user_id": str(user_id),
            "amount": amount,
            "category": category,
            "description": description,
            "tags": tags or [],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": datetime.now().isoformat(),
            "weekday": datetime.now().strftime("%A"),
            "month": datetime.now().strftime("%B"),
            "year": datetime.now().strftime("%Y")
        }
        
        expenses = load_data(EXPENSES_FILE, [])
        expenses.append(expense)
        save_data(EXPENSES_FILE, expenses)
        
        # Update user stats
        AdvancedExpenseManager.update_user_stats(user_id)
        
        return expense
    
    @staticmethod
    def update_user_stats(user_id: str):
        """Update user statistics"""
        user_stats = load_data(USERS_FILE, {})
        if user_id not in user_stats:
            user_stats[user_id] = {
                "total_expenses": 0,
                "total_entries": 0,
                "average_daily": 0,
                "most_used_category": "",
                "last_active": datetime.now().isoformat()
            }
        
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == user_id]
        
        if user_expenses:
            total = sum(e["amount"] for e in user_expenses)
            user_stats[user_id]["total_expenses"] = total
            user_stats[user_id]["total_entries"] = len(user_expenses)
            user_stats[user_id]["last_active"] = datetime.now().isoformat()
            
            # Find most used category
            category_count = {}
            for e in user_expenses:
                cat = e.get("category", "unknown")
                category_count[cat] = category_count.get(cat, 0) + 1
            
            if category_count:
                user_stats[user_id]["most_used_category"] = max(category_count, key=category_count.get)
        
        save_data(USERS_FILE, user_stats)
    
    @staticmethod
    def get_expenses_by_period(user_id: str, period: str = "month") -> Tuple[List, Dict]:
        """Get expenses by time period with analysis"""
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        now = datetime.now()
        
        if period == "today":
            target_date = now.strftime("%Y-%m-%d")
            filtered = [e for e in user_expenses if e["date"] == target_date]
        
        elif period == "week":
            week_ago = now - timedelta(days=7)
            filtered = [
                e for e in user_expenses 
                if datetime.strptime(e["date"], "%Y-%m-%d") >= week_ago
            ]
        
        elif period == "month":
            month_ago = now - timedelta(days=30)
            filtered = [
                e for e in user_expenses 
                if datetime.strptime(e["date"], "%Y-%m-%d") >= month_ago
            ]
        
        elif period == "quarter":
            quarter_ago = now - timedelta(days=90)
            filtered = [
                e for e in user_expenses 
                if datetime.strptime(e["date"], "%Y-%m-%d") >= quarter_ago
            ]
        
        elif period == "year":
            year_ago = now - timedelta(days=365)
            filtered = [
                e for e in user_expenses 
                if datetime.strptime(e["date"], "%Y-%m-%d") >= year_ago
            ]
        
        elif period == "last_month":
            last_month = now.replace(day=1) - timedelta(days=1)
            month_start = last_month.replace(day=1)
            month_end = last_month
            
            filtered = [
                e for e in user_expenses
                if month_start <= datetime.strptime(e["date"], "%Y-%m-%d") <= month_end
            ]
        
        else:
            filtered = user_expenses
        
        # Analysis
        analysis = {
            "total": sum(e["amount"] for e in filtered),
            "count": len(filtered),
            "average": sum(e["amount"] for e in filtered) / len(filtered) if filtered else 0,
            "max": max((e["amount"] for e in filtered), default=0),
            "min": min((e["amount"] for e in filtered), default=0)
        }
        
        # Category analysis
        category_totals = {}
        for e in filtered:
            cat = e.get("category", "unknown")
            category_totals[cat] = category_totals.get(cat, 0) + e["amount"]
        
        analysis["category_totals"] = category_totals
        
        # Daily analysis
        daily_totals = {}
        for e in filtered:
            day = e["date"]
            daily_totals[day] = daily_totals.get(day, 0) + e["amount"]
        
        analysis["daily_totals"] = daily_totals
        
        return filtered, analysis
    
    @staticmethod
    def generate_pie_chart(user_id: str, period: str = "month") -> io.BytesIO:
        """Generate pie chart for expenses"""
        _, analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, period)
        category_totals = analysis["category_totals"]
        
        if not category_totals:
            return None
        
        # Prepare data
        categories = list(category_totals.keys())
        amounts = list(category_totals.values())
        
        # Get Persian category names
        category_map = {
            "food": "🍔 غذا",
            "transport": "🚕 حمل‌ونقل",
            "shopping": "🛒 خرید",
            "house": "🏠 خانه",
            "health": "💊 سلامت",
            "entertainment": "🎬 تفریح",
            "education": "📚 آموزش",
            "clothing": "👕 پوشاک",
            "tech": "💻 فناوری",
            "gift": "🎁 هدیه",
            "travel": "✈️ سفر",
            "smoking": "🚬 دخانیات",
            "pets": "🐕 حیوانات",
            "party": "🎪 مهمانی",
            "mobile": "📱 موبایل"
        }
        
        labels = [category_map.get(cat, cat) for cat in categories]
        
        # Create pie chart
        plt.figure(figsize=(10, 8))
        colors = plt.cm.Set3(range(len(categories)))
        wedges, texts, autotexts = plt.pie(
            amounts, 
            labels=labels, 
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%\n{int(pct*sum(amounts)/100):,}",
            startangle=90
        )
        
        plt.title(f'توزیع هزینه‌ها ({period})', fontsize=16, fontname='B Nazanin', fontweight='bold')
        plt.axis('equal')
        
        # Save to bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    @staticmethod
    def generate_bar_chart(user_id: str, period: str = "month") -> io.BytesIO:
        """Generate bar chart for expenses"""
        _, analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, period)
        category_totals = analysis["category_totals"]
        
        if not category_totals:
            return None
        
        # Prepare data
        categories = list(category_totals.keys())
        amounts = list(category_totals.values())
        
        # Get Persian category names
        category_map = {
            "food": "🍔 غذا",
            "transport": "🚕 حمل‌ونقل",
            "shopping": "🛒 خرید",
            "house": "🏠 خانه",
            "health": "💊 سلامت",
            "entertainment": "🎬 تفریح",
            "education": "📚 آموزش",
            "clothing": "👕 پوشاک",
            "tech": "💻 فناوری",
            "gift": "🎁 هدیه",
            "travel": "✈️ سفر",
            "smoking": "🚬 دخانیات",
            "pets": "🐕 حیوانات",
            "party": "🎪 مهمانی",
            "mobile": "📱 موبایل"
        }
        
        labels = [category_map.get(cat, cat) for cat in categories]
        
        # Create bar chart
        plt.figure(figsize=(12, 8))
        bars = plt.barh(labels, amounts, color=plt.cm.Set3(range(len(categories))))
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            plt.text(width + max(amounts)*0.01, bar.get_y() + bar.get_height()/2,
                    f'{width:,} تومان',
                    va='center', ha='left', fontsize=10)
        
        plt.title(f'هزینه‌ها بر اساس دسته ({period})', fontsize=16, fontname='B Nazanin', fontweight='bold')
        plt.xlabel('مبلغ (تومان)', fontname='B Nazanin')
        plt.tight_layout()
        
        # Save to bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer
    
    @staticmethod
    def export_to_csv(user_id: str) -> str:
        """Export expenses to CSV format"""
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        if not user_expenses:
            return None
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['تاریخ', 'زمان', 'دسته‌بندی', 'مبلغ', 'توضیحات', 'تگ‌ها'])
        
        # Write data
        for exp in sorted(user_expenses, key=lambda x: x['timestamp'], reverse=True):
            writer.writerow([
                exp['date'],
                exp['time'],
                AdvancedExpenseManager.get_category_name(f"cat_{exp.get('category', 'unknown')}"),
                exp['amount'],
                exp.get('description', ''),
                ', '.join(exp.get('tags', []))
            ])
        
        return output.getvalue()
    
    @staticmethod
    def get_category_name(callback_data: str) -> str:
        """Convert callback to Persian category name"""
        category_map = {
            "food": "🍔 غذا و رستوران",
            "transport": "🚕 حمل و نقل",
            "shopping": "🛒 خرید روزانه",
            "house": "🏠 خانه و قبوض",
            "health": "💊 سلامت و درمان",
            "entertainment": "🎬 تفریح و سرگرمی",
            "education": "📚 آموزش و کتاب",
            "clothing": "👕 پوشاک و مد",
            "tech": "💻 فناوری و اینترنت",
            "gift": "🎁 هدیه و مناسبت",
            "travel": "✈️ سفر و گردش",
            "smoking": "🚬 سیگار و دخانیات",
            "pets": "🐕 حیوانات خانگی",
            "party": "🎪 مهمانی و مراسم",
            "mobile": "📱 شارژ و اینترنت"
        }
        
        cat_key = callback_data.replace("cat_", "")
        return category_map.get(cat_key, "سایر")
    
    @staticmethod
    def get_statistics(user_id: str) -> Dict:
        """Get comprehensive statistics"""
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        if not user_expenses:
            return {}
        
        stats = {
            "total_expenses": sum(e["amount"] for e in user_expenses),
            "total_count": len(user_expenses),
            "average_per_day": 0,
            "most_expensive": max(user_expenses, key=lambda x: x["amount"]),
            "most_used_category": "",
            "expenses_by_month": {},
            "expenses_by_weekday": {}
        }
        
        # Calculate daily average
        dates = set(e["date"] for e in user_expenses)
        if dates:
            days_count = len(dates)
            stats["average_per_day"] = stats["total_expenses"] / days_count
        
        # Find most used category
        category_count = {}
        for e in user_expenses:
            cat = e.get("category", "unknown")
            category_count[cat] = category_count.get(cat, 0) + 1
        
        if category_count:
            stats["most_used_category"] = max(category_count, key=category_count.get)
        
        # Expenses by month
        for e in user_expenses:
            month = e["date"][:7]  # YYYY-MM
            stats["expenses_by_month"][month] = stats["expenses_by_month"].get(month, 0) + e["amount"]
        
        # Expenses by weekday
        weekday_map = {
            "Monday": "دوشنبه",
            "Tuesday": "سه‌شنبه",
            "Wednesday": "چهارشنبه",
            "Thursday": "پنج‌شنبه",
            "Friday": "جمعه",
            "Saturday": "شنبه",
            "Sunday": "یک‌شنبه"
        }
        
        for e in user_expenses:
            try:
                date_obj = datetime.strptime(e["date"], "%Y-%m-%d")
                weekday = weekday_map[date_obj.strftime("%A")]
                stats["expenses_by_weekday"][weekday] = stats["expenses_by_weekday"].get(weekday, 0) + e["amount"]
            except:
                pass
        
        return stats
    
    @staticmethod
    def create_backup(user_id: str) -> Dict:
        """Create backup of user data"""
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        backup = {
            "user_id": user_id,
            "backup_date": datetime.now().isoformat(),
            "total_records": len(user_expenses),
            "total_amount": sum(e["amount"] for e in user_expenses),
            "data": user_expenses
        }
        
        # Save backup
        backups = load_data(BACKUP_FILE, [])
        backups.append(backup)
        save_data(BACKUP_FILE, backups)
        
        return backup
    
    @staticmethod
    def search_expenses(user_id: str, query: str, category: str = None, 
                       min_amount: int = None, max_amount: int = None,
                       start_date: str = None, end_date: str = None) -> List:
        """Advanced search in expenses"""
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        results = user_expenses
        
        # Filter by category
        if category:
            results = [e for e in results if e.get("category") == category]
        
        # Filter by amount range
        if min_amount is not None:
            results = [e for e in results if e["amount"] >= min_amount]
        
        if max_amount is not None:
            results = [e for e in results if e["amount"] <= max_amount]
        
        # Filter by date range
        if start_date:
            results = [e for e in results if e["date"] >= start_date]
        
        if end_date:
            results = [e for e in results if e["date"] <= end_date]
        
        # Filter by text query
        if query:
            query = query.lower()
            results = [
                e for e in results 
                if query in str(e.get("description", "")).lower() or 
                   query in str(e.get("category", "")).lower() or
                   query in str(e["amount"])
            ]
        
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)

# ========== 🤖 Main Commands ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /start"""
    user = update.effective_user
    
    welcome_text = f"""
🤖 **ربات مدیریت هوشمند هزینه‌ها (نسخه حرفه‌ای)**

سلام {user.first_name} 👋
به ربات مدیریت هزینه خوش آمدید!

🎯 **ویژگی‌های جدید:**
• ثبت سریع با کیبورد ⚡
• نمودارهای رنگی 📊
• گزارش‌های پیشرفته 📈
• پشتیبان‌گیری خودکار 📁
• جستجوی هوشمند 🔍
• آمار و تحلیل 📊
• هشدارهای خودکار 🔔

📱 **از کیبورد پایین انتخاب کنید:**
"""
    
    # Clear any previous data
    context.user_data.clear()
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard_manager.get_main_keyboard(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /help"""
    help_text = """
📚 **راهنمای جامع ربات**

🔹 **ثبت سریع هزینه:**
• `50 غذا` - ثبت ۵۰ هزار تومان برای غذا
• `100 ترافیک ناهار` - ثبت با توضیح
• از کیبورد سریع استفاده کنید

🔹 **منوهای اصلی:**
➕ هزینه جدید - ثبت هزینه کامل
💰 درآمد جدید - ثبت درآمد
📊 گزارش‌ها - گزارش‌های پیشرفته
🎯 بودجه‌ها - مدیریت بودجه
📈 آمار - آمار و تحلیل
🔄 مدیریت - تنظیمات و خروجی
⚡ سریع - ثبت فوق‌سریع

🔹 **دستورات ویژه:**
/start - راه‌اندازی مجدد
/stats - آمار شخصی
/export - خروجی داده‌ها
/backup - پشتیبان‌گیری
/search - جستجو
/help - این راهنما

🎁 **این ربات کاملاً رایگان است!**
"""
    
    await update.message.reply_text(
        help_text,
        reply_markup=keyboard_manager.get_back_keyboard(),
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /stats"""
    user_id = str(update.effective_user.id)
    stats = AdvancedExpenseManager.get_statistics(user_id)
    
    if not stats:
        text = "📊 **هنوز هیچ آماری ثبت نکرده‌اید!**\n\nاولین هزینه خود را ثبت کنید."
    else:
        text = f"""
📊 **آمار شخصی شما**

💰 **کل هزینه‌ها:** {stats['total_expenses']:,} تومان
📝 **تعداد ثبت‌ها:** {stats['total_count']} مورد
📅 **میانگین روزانه:** {int(stats['average_per_day']):,} تومان

🏷️ **پرتکرارترین دسته:** {AdvancedExpenseManager.get_category_name(f"cat_{stats['most_used_category']}")}
💸 **گران‌ترین خرید:** {stats['most_expensive']['amount']:,} تومان

📈 **روند هزینه‌ها:**
"""
        
        # Add monthly trends (last 3 months)
        months = list(stats["expenses_by_month"].keys())[-3:]
        for month in months:
            text += f"• {month}: {stats['expenses_by_month'][month]:,} تومان\n"
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard_manager.get_back_keyboard(),
        parse_mode="Markdown"
    )

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /export"""
    await update.message.reply_text(
        "📤 **خروجی گرفتن از داده‌ها**\n\nلطفاً فرمت مورد نظر را انتخاب کنید:",
        reply_markup=menu.export_menu(),
        parse_mode="Markdown"
    )

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /backup"""
    user_id = str(update.effective_user.id)
    backup = AdvancedExpenseManager.create_backup(user_id)
    
    text = f"""
✅ **پشتیبان‌گیری موفق**

📅 تاریخ پشتیبان: {backup['backup_date'][:10]}
📊 تعداد رکوردها: {backup['total_records']} مورد
💰 مجموع مبلغ: {backup['total_amount']:,} تومان

📁 پشتیبان شما با موفقیت ذخیره شد.
برای بازیابی به منوی مدیریت مراجعه کنید.
"""
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard_manager.get_back_keyboard(),
        parse_mode="Markdown"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /search"""
    await update.message.reply_text(
        "🔍 **جستجوی پیشرفته**\n\nبرای جستجو عبارت خود را وارد کنید:\n\n"
        "مثال‌ها:\n"
        "• `غذا` - جستجو در توضیحات\n"
        "• `50000` - هزینه‌های بیشتر از ۵۰ هزار\n"
        "• `2024-01` - هزینه‌های دی ماه\n\n"
        "یا برای جستجوی پیشرفته از دکمه زیر استفاده کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 جستجوی پیشرفته", callback_data="search_advanced")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]),
        parse_mode="Markdown"
    )

# ========== 🎯 Bottom Keyboard Handler ==========
async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for bottom keyboard buttons"""
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    
    print(f"Keyboard button: {text} by user: {user_id}")
    
    # Quick expense buttons (fast registration)
    quick_map = {
        "🍔 غذا": "food",
        "🚕 حمل‌ونقل": "transport", 
        "🛒 خرید": "shopping",
        "🏠 خانه": "house",
        "💊 سلامت": "health",
        "🎬 تفریح": "entertainment"
    }
    
    if text in quick_map:
        context.user_data["quick_category"] = quick_map[text]
        await update.message.reply_text(
            f"✅ دسته انتخاب شد: {text}\n\n💰 لطفاً مبلغ را وارد کنید:\nمثال: 50000 یا 50هزار",
            reply_markup=keyboard_manager.get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        context.user_data["awaiting_quick_amount"] = True
        return
    
    # Main menu buttons
    if text == "➕ هزینه جدید":
        await update.message.reply_text(
            "🏷️ **انتخاب دسته‌بندی**\n\nلطفاً دسته هزینه را انتخاب کنید:",
            reply_markup=menu.categories_menu(),
            parse_mode="Markdown"
        )
    
    elif text == "💰 درآمد جدید":
        await update.message.reply_text(
            "💰 **ثبت درآمد جدید**\n\nلطفاً مبلغ درآمد را انتخاب کنید:",
            reply_markup=menu.amounts_menu(),
            parse_mode="Markdown"
        )
    
    elif text == "📊 گزارش‌ها":
        await update.message.reply_text(
            "📊 **گزارش‌ها و آمار پیشرفته**\n\nلطفاً نوع گزارش را انتخاب کنید:",
            reply_markup=menu.reports_menu(),
            parse_mode="Markdown"
        )
    
    elif text == "🎯 بودجه‌ها":
        await update.message.reply_text(
            "🎯 **مدیریت بودجه پیشرفته**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=menu.budgets_menu(),
            parse_mode="Markdown"
        )
    
    elif text == "📈 آمار":
        await update.message.reply_text(
            "📈 **آمار و تحلیل پیشرفته**\n\nلطفاً نوع آمار را انتخاب کنید:",
            reply_markup=menu.stats_menu(),
            parse_mode="Markdown"
        )
    
    elif text == "🔄 مدیریت":
        await update.message.reply_text(
            "🔄 **مدیریت و تنظیمات**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=menu.management_menu(),
            parse_mode="Markdown"
        )
    
    elif text == "⚡ سریع":
        await update.message.reply_text(
            "⚡ **ثبت فوق‌سریع**\n\nلطفاً دسته را انتخاب کنید:",
            reply_markup=keyboard_manager.get_quick_keyboard(),
            parse_mode="Markdown"
        )
    
    elif text == "🏠 منوی اصلی":
        await start(update, context)
    
    elif text == "🔙 بازگشت":
        await update.message.reply_text(
            "به منوی اصلی بازگشتید.",
            reply_markup=keyboard_manager.get_main_keyboard()
        )
    
    elif text == "❌ لغو":
        await update.message.reply_text(
            "❌ عملیات لغو شد.",
            reply_markup=keyboard_manager.get_main_keyboard()
        )
        context.user_data.clear()
    
    elif text == "📝 توضیح":
        if context.user_data.get("awaiting_quick_amount"):
            await update.message.reply_text(
                "📝 لطفاً توضیحات را وارد کنید:\n(اختیاری - برای صرف نظر کردن 'بعداً' بنویسید)",
                reply_markup=keyboard_manager.get_cancel_keyboard(),
                parse_mode="Markdown"
            )
            context.user_data["awaiting_quick_description"] = True
        else:
            await update.message.reply_text(
                "ابتدا یک دسته انتخاب کنید.",
                reply_markup=keyboard_manager.get_quick_keyboard()
            )
    
    else:
        # Handle quick expense amount input
        if context.user_data.get("awaiting_quick_amount"):
            amount = parse_amount(text)
            if amount and amount > 0:
                context.user_data["quick_amount"] = amount
                context.user_data.pop("awaiting_quick_amount", None)
                
                await update.message.reply_text(
                    f"✅ مبلغ ثبت شد: {amount:,} تومان\n\n"
                    f"📝 برای افزودن توضیح دکمه '📝 توضیح' را بزنید\n"
                    f"یا برای ثبت بدون توضیح '✅ ثبت' بنویسید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 افزودن توضیح", callback_data="add_description")],
                        [InlineKeyboardButton("✅ ثبت نهایی", callback_data="confirm_quick")]
                    ]),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    "❌ مبلغ نامعتبر!\n\nلطفاً عدد معتبر وارد کنید:\nمثال: 50000 یا 50هزار",
                    reply_markup=keyboard_manager.get_cancel_keyboard()
                )
        
        # Handle quick description input
        elif context.user_data.get("awaiting_quick_description"):
            description = text if text != "بعداً" else ""
            context.user_data["quick_description"] = description
            context.user_data.pop("awaiting_quick_description", None)
            
            # Complete the expense
            category = context.user_data.get("quick_category", "food")
            amount = context.user_data.get("quick_amount", 0)
            
            if amount > 0:
                expense = AdvancedExpenseManager.add_expense(
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    description=description
                )
                
                category_name = AdvancedExpenseManager.get_category_name(f"cat_{category}")
                await update.message.reply_text(
                    f"✅ **ثبت فوق‌سریع موفق!**\n\n"
                    f"💰 مبلغ: {amount:,} تومان\n"
                    f"🏷️ دسته: {category_name}\n"
                    f"📝 توضیح: {description if description else 'بدون توضیح'}\n"
                    f"🕐 زمان: {expense['time']}",
                    reply_markup=keyboard_manager.get_main_keyboard(),
                    parse_mode="Markdown"
                )
                
                context.user_data.clear()
            else:
                await update.message.reply_text(
                    "❌ خطا در ثبت. لطفاً مجدد تلاش کنید.",
                    reply_markup=keyboard_manager.get_main_keyboard()
                )
        
        else:
            # Handle natural language input
            await handle_natural_input(update, context, text)

# ========== 🎯 Natural Language Input Handler ==========
async def handle_natural_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle natural language input like '50 غذا'"""
    # Pattern: amount + category + optional description
    patterns = [
        r'(\d+[\d,]*)\s*(هزار|میلیون|میلیارد)?\s*(.*)',
        r'(\d+[\d,]*)\s*(.*)'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            amount_str = match.group(1)
            multiplier = match.group(2) if len(match.groups()) > 1 and match.group(2) else ""
            rest = match.group(3) if len(match.groups()) > 2 else ""
            
            amount = parse_amount(amount_str + multiplier)
            
            if amount and amount > 0:
                # Try to extract category from text
                category_keywords = {
                    "غذا": "food",
                    "رستوران": "food",
                    "سفارش": "food",
                    "ترافیک": "transport",
                    "تاکسی": "transport",
                    "اتوبوس": "transport",
                    "مترو": "transport",
                    "بنزین": "transport",
                    "خرید": "shopping",
                    "مارکت": "shopping",
                    "سوپر": "shopping",
                    "خانه": "house",
                    "اجاره": "house",
                    "قبض": "house",
                    "برق": "house",
                    "گاز": "house",
                    "آب": "house",
                    "سلامت": "health",
                    "دکتر": "health",
                    "دارو": "health",
                    "تفریح": "entertainment",
                    "سینما": "entertainment",
                    "کافه": "entertainment",
                    "آموزش": "education",
                    "کتاب": "education",
                    "کلاس": "education",
                    "پوشاک": "clothing",
                    "لباس": "clothing",
                    "کفش": "clothing",
                    "فناوری": "tech",
                    "موبایل": "tech",
                    "لپتاپ": "tech",
                    "هدیه": "gift",
                    "کادو": "gift",
                    "سفر": "travel",
                    "مسافرت": "travel"
                }
                
                category = "food"  # default
                description = ""
                
                for keyword, cat in category_keywords.items():
                    if keyword in rest:
                        category = cat
                        description = rest.replace(keyword, "").strip()
                        break
                
                if not description:
                    description = rest.strip()
                
                # Register expense
                expense = AdvancedExpenseManager.add_expense(
                    user_id=update.effective_user.id,
                    amount=amount,
                    category=category,
                    description=description if description else "ثبت سریع"
                )
                
                category_name = AdvancedExpenseManager.get_category_name(f"cat_{category}")
                await update.message.reply_text(
                    f"✅ **ثبت هوشمند موفق!**\n\n"
                    f"💰 مبلغ: {amount:,} تومان\n"
                    f"🏷️ دسته: {category_name}\n"
                    f"📝 توضیح: {description if description else 'ثبت سریع'}\n"
                    f"🕐 زمان: {expense['time']}",
                    reply_markup=keyboard_manager.get_main_keyboard(),
                    parse_mode="Markdown"
                )
                return
    
    # If no pattern matched, show help
    await update.message.reply_text(
        f"برای ثبت سریع هزینه:\n"
        f"• `50 غذا` - ۵۰ هزار تومان غذا\n"
        f"• `100 ترافیک تاکسی` - با توضیح\n"
        f"• از کیبورد سریع استفاده کنید\n\n"
        f"یا از منوی اصلی انتخاب کنید:",
        reply_markup=keyboard_manager.get_main_keyboard()
    )

# ========== 🎯 Dropdown Button Handlers ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for all dropdown buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    print(f"Button clicked: {data} by user: {user_id}")
    
    # 📌 Category handlers
    if data.startswith("cat_"):
        if data == "cat_new":
            await query.edit_message_text(
                "➕ **ایجاد دسته جدید**\n\n"
                "نام دسته جدید را وارد کنید:\n"
                "(حداکثر 20 کاراکتر)",
                parse_mode="Markdown"
            )
            context.user_data["awaiting_new_category"] = True
        else:
            await handle_category_selection(query, data, context)
    
    # 📌 Amount handlers
    elif data.startswith("amount_"):
        await handle_amount_selection(query, data, user_id, context)
    
    # 📌 Report handlers
    elif data.startswith("report_"):
        await handle_report_selection(query, data, user_id)
    
    # 📌 Chart handlers
    elif data.startswith("chart_"):
        await handle_chart_selection(query, data, user_id)
    
    # 📌 Budget handlers
    elif data.startswith("budget_"):
        await handle_budget_selection(query, data, user_id)
    
    # 📌 Stats handlers
    elif data.startswith("stats_"):
        await handle_stats_selection(query, data, user_id)
    
    # 📌 Management handlers
    elif data.startswith("export_") or data.startswith("backup_") or data == "settings" or data == "manage_categories" or data == "clean_data" or data == "system_stats":
        await handle_management_selection(query, data, user_id, context)
    
    # 📌 Search handlers
    elif data == "search_advanced":
        await handle_advanced_search(query, context)
    
    # 📌 Quick expense handlers
    elif data == "add_description":
        await query.edit_message_text(
            "📝 لطفاً توضیحات را وارد کنید:\n(اختیاری - برای صرف نظر 'بعداً' بنویسید)",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_quick_description"] = True
    
    elif data == "confirm_quick":
        category = context.user_data.get("quick_category", "food")
        amount = context.user_data.get("quick_amount", 0)
        description = context.user_data.get("quick_description", "")
        
        if amount > 0:
            expense = AdvancedExpenseManager.add_expense(
                user_id=user_id,
                amount=amount,
                category=category,
                description=description
            )
            
            category_name = AdvancedExpenseManager.get_category_name(f"cat_{category}")
            await query.edit_message_text(
                f"✅ **ثبت فوق‌سریع موفق!**\n\n"
                f"💰 مبلغ: {amount:,} تومان\n"
                f"🏷️ دسته: {category_name}\n"
                f"📝 توضیح: {description if description else 'بدون توضیح'}\n"
                f"🕐 زمان: {expense['time']}",
                reply_markup=keyboard_manager.get_main_keyboard(),
                parse_mode="Markdown"
            )
            
            context.user_data.clear()
        else:
            await query.edit_message_text(
                "❌ خطا در ثبت. لطفاً مجدد تلاش کنید.",
                reply_markup=keyboard_manager.get_main_keyboard()
            )
    
    # 📌 Back handlers
    elif data.startswith("back_"):
        await handle_back_button(query, data)
    
    # 📌 Other handlers
    elif data == "restart":
        await start_callback(query)
    
    elif data == "apply_coupon":
        await apply_coupon(query, context)
    
    elif data in ["confirm_yes", "confirm_no"]:
        if data == "confirm_yes":
            await query.edit_message_text(
                "✅ **عملیات تایید شد!**\n\n"
                "در حال انجام عملیات...",
                reply_markup=menu.back_menu("main"),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ **عملیات لغو شد.**\n\n"
                "به منوی اصلی بازگشتید.",
                reply_markup=keyboard_manager.get_main_keyboard(),
                parse_mode="Markdown"
            )

# ========== 🎯 Helper Functions for Handlers ==========
async def handle_category_selection(query, data, context):
    """Category selection handler"""
    category_name = AdvancedExpenseManager.get_category_name(data)
    
    # Save selected category in context.user_data
    context.user_data["selected_category"] = data.replace("cat_", "")
    
    await query.edit_message_text(
        f"✅ **دسته انتخاب شد:** {category_name}\n\n"
        f"💰 لطفاً مبلغ هزینه را انتخاب کنید:",
        reply_markup=menu.amounts_menu(),
        parse_mode="Markdown"
    )

async def handle_amount_selection(query, data, user_id, context):
    """Amount selection handler"""
    if data == "amount_custom":
        await query.edit_message_text(
            "✍️ **مبلغ دلخواه**\n\n"
            "لطفاً مبلغ را به عدد وارد کنید:\n"
            "مثال: 15000 یا 50هزار\n\n"
            "برای لغو از دکمه ❌ لغو استفاده کنید.",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_custom_amount"] = True
        context.user_data["awaiting_amount_for"] = "expense"
        return
    
    amount = int(data.replace("amount_", ""))
    
    # Save amount in context.user_data
    context.user_data["selected_amount"] = amount
    
    await query.edit_message_text(
        f"💰 **مبلغ انتخاب شد:** {amount:,} تومان\n\n"
        f"📝 لطفاً توضیحات هزینه را وارد کنید:\n"
        f"(می‌توانید خالی بگذارید یا 'لغو' تایپ کنید)\n\n"
        f"برای لغو از دکمه ❌ لغو استفاده کنید.",
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_description"] = True

async def handle_report_selection(query, data, user_id):
    """Report selection handler"""
    report_type = data.replace("report_", "")
    
    expenses, analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, report_type)
    
    if not expenses:
        period_names = {
            "today": "امروز",
            "week": "این هفته",
            "month": "این ماه",
            "quarter": "سه ماهه",
            "year": "امسال",
            "last_month": "ماه قبل"
        }
        period_name = period_names.get(report_type, report_type)
        text = f"📭 **هیچ هزینه‌ای برای {period_name} ثبت نکرده‌اید!**"
    else:
        period_names = {
            "today": "امروز",
            "week": "این هفته",
            "month": "این ماه",
            "quarter": "سه ماه اخیر",
            "year": "امسال",
            "last_month": "ماه قبل"
        }
        period_name = period_names.get(report_type, report_type)
        
        text = f"📊 **گزارش {period_name}**\n\n"
        text += f"💰 **مجموع هزینه‌ها:** {analysis['total']:,} تومان\n"
        text += f"📝 **تعداد:** {analysis['count']} مورد\n"
        text += f"📈 **میانگین هر مورد:** {int(analysis['average']):,} تومان\n"
        text += f"⚡ **بیشترین:** {analysis['max']:,} تومان\n"
        text += f"📉 **کمترین:** {analysis['min']:,} تومان\n\n"
        
        if analysis['category_totals']:
            text += "🏷️ **بر اساس دسته:**\n"
            for cat, amount in sorted(analysis['category_totals'].items(), key=lambda x: x[1], reverse=True)[:5]:
                cat_name = AdvancedExpenseManager.get_category_name(f"cat_{cat}")
                percentage = (amount / analysis['total']) * 100
                text += f"• {cat_name}: {amount:,} تومان ({percentage:.1f}%)\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 نمودار دایره‌ای", callback_data=f"chart_pie_{report_type}")],
            [InlineKeyboardButton("📈 نمودار میله‌ای", callback_data=f"chart_bar_{report_type}")],
            [InlineKeyboardButton("📊 گزارش‌های دیگر", callback_data="back_reports")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")]
        ]),
        parse_mode="Markdown"
    )

async def handle_chart_selection(query, data, user_id):
    """Chart selection handler"""
    chart_type = data.replace("chart_", "")
    
    if "_" in chart_type:
        chart_type, period = chart_type.split("_")
    else:
        period = "month"
    
    if chart_type == "pie":
        chart_buffer = AdvancedExpenseManager.generate_pie_chart(user_id, period)
        chart_name = "دایره‌ای"
    else:  # bar
        chart_buffer = AdvancedExpenseManager.generate_bar_chart(user_id, period)
        chart_name = "میله‌ای"
    
    if chart_buffer:
        await query.message.reply_photo(
            photo=chart_buffer,
            caption=f"📊 **نمودار {chart_name} هزینه‌ها**\n\nدوره: {period}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 گزارش‌ها", callback_data="back_reports")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")]
            ])
        )
        await query.delete_message()
    else:
        await query.edit_message_text(
            "📭 **داده‌ای برای رسم نمودار وجود ندارد!**\n\nلطفاً ابتدا هزینه‌ای ثبت کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 گزارش‌ها", callback_data="back_reports")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")]
            ])
        )

async def handle_budget_selection(query, data, user_id):
    """Budget operation selection handler"""
    action = data.replace("budget_", "")
    
    if action == "create":
        await query.edit_message_text(
            "🎯 **ایجاد بودجه جدید**\n\nلطفاً دسته‌بندی را انتخاب کنید:",
            reply_markup=menu.categories_menu(),
            parse_mode="Markdown"
        )
    
    elif action == "view":
        budgets = load_data(BUDGETS_FILE, {})
        user_budgets = budgets.get(user_id, [])
        
        if not user_budgets:
            text = "🎯 **بودجه‌ای تنظیم نکرده‌اید!**\n\nبرای ایجاد بودجه جدید روی '➕ ایجاد بودجه جدید' کلیک کنید."
        else:
            text = "🎯 **بودجه‌های شما**\n\n"
            for i, budget in enumerate(user_budgets, 1):
                cat_name = AdvancedExpenseManager.get_category_name(f"cat_{budget.get('category', 'unknown')}")
                text += f"{i}. {cat_name}: {budget.get('amount', 0):,} تومان\n"
                if budget.get('description'):
                    text += f"   📌 {budget['description']}\n"
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("budgets"),
            parse_mode="Markdown"
        )
    
    elif action == "smart":
        # Smart budget suggestion
        expenses, analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, "month")
        
        if not expenses:
            text = "📊 **برای پیشنهاد بودجه هوشمند نیاز به داده‌های بیشتری دارید.**\n\nلطفاً حداقل ۱۰ هزینه ثبت کنید."
        else:
            text = "🎯 **پیشنهاد بودجه هوشمند**\n\n"
            text += "بر اساس هزینه‌های ماه گذشته:\n\n"
            
            for cat, amount in sorted(analysis['category_totals'].items(), key=lambda x: x[1], reverse=True)[:5]:
                cat_name = AdvancedExpenseManager.get_category_name(f"cat_{cat}")
                suggested = int(amount * 0.9)  # 10% less than last month
                text += f"• {cat_name}: {suggested:,} تومان\n"
            
            text += "\n💡 **نکته:** این پیشنهادات ۱۰٪ کمتر از ماه قبل هستند تا در هزینه‌ها صرفه‌جویی کنید."
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("budgets"),
            parse_mode="Markdown"
        )
    
    elif action == "compare":
        # Compare with previous month
        current_month, current_analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, "month")
        last_month, last_analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, "last_month")
        
        if not current_month or not last_month:
            text = "📊 **برای مقایسه نیاز به داده‌های دو ماه متوالی دارید.**"
        else:
            text = "📊 **مقایسه با ماه قبل**\n\n"
            text += f"💰 **ماه جاری:** {current_analysis['total']:,} تومان\n"
            text += f"💰 **ماه قبل:** {last_analysis['total']:,} تومان\n\n"
            
            difference = current_analysis['total'] - last_analysis['total']
            if difference > 0:
                text += f"📈 **افزایش:** {difference:,} تومان\n"
                text += f"📊 **درصد:** +{(difference/last_analysis['total']*100):.1f}%\n"
            else:
                text += f"📉 **کاهش:** {abs(difference):,} تومان\n"
                text += f"📊 **درصد:** {(difference/last_analysis['total']*100):.1f}%\n"
            
            text += "\n💡 **تحلیل:**\n"
            if difference > (last_analysis['total'] * 0.1):
                text += "هزینه‌های شما نسبت به ماه قبل افزایش قابل توجهی داشته‌است."
            elif difference < -(last_analysis['total'] * 0.1):
                text += "آفرین! در هزینه‌های خود صرفه‌جویی کرده‌اید."
            else:
                text += "هزینه‌های شما نسبتاً ثابت بوده‌است."
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("budgets"),
            parse_mode="Markdown"
        )
    
    else:
        text = f"🔧 **عملیات {action}**\n\n(این بخش در حال توسعه است...)"
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("budgets"),
            parse_mode="Markdown"
        )

async def handle_stats_selection(query, data, user_id):
    """Statistics selection handler"""
    action = data.replace("stats_", "")
    
    if action == "overview":
        stats = AdvancedExpenseManager.get_statistics(user_id)
        
        if not stats:
            text = "📊 **هنوز هیچ آماری ثبت نکرده‌اید!**\n\nاولین هزینه خود را ثبت کنید."
        else:
            text = f"""
📊 **آمار کلی شما**

💰 **کل هزینه‌ها:** {stats['total_expenses']:,} تومان
📝 **تعداد ثبت‌ها:** {stats['total_count']} مورد
📅 **میانگین روزانه:** {int(stats['average_per_day']):,} تومان

🏆 **رکوردها:**
• گران‌ترین: {stats['most_expensive']['amount']:,} تومان
• پرتکرارترین دسته: {AdvancedExpenseManager.get_category_name(f"cat_{stats['most_used_category']}")}

📈 **توزیع روزهای هفته:**
"""
            for day, amount in sorted(stats['expenses_by_weekday'].items()):
                text += f"• {day}: {amount:,} تومان\n"
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("stats"),
            parse_mode="Markdown"
        )
    
    elif action == "top":
        expenses = load_data(EXPENSES_FILE, [])
        user_expenses = [e for e in expenses if e["user_id"] == str(user_id)]
        
        if not user_expenses:
            text = "📭 **هیچ هزینه‌ای ثبت نکرده‌اید!**"
        else:
            top_expenses = sorted(user_expenses, key=lambda x: x['amount'], reverse=True)[:10]
            
            text = "🏆 **گران‌ترین هزینه‌های شما**\n\n"
            for i, exp in enumerate(top_expenses, 1):
                cat_name = AdvancedExpenseManager.get_category_name(f"cat_{exp.get('category', 'unknown')}")
                text += f"{i}. {exp['amount']:,} تومان - {cat_name}\n"
                if exp.get('description'):
                    text += f"   📌 {exp['description']}\n"
                text += f"   📅 {exp['date']}\n"
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("stats"),
            parse_mode="Markdown"
        )
    
    elif action == "forecast":
        expenses, analysis = AdvancedExpenseManager.get_expenses_by_period(user_id, "month")
        
        if not expenses:
            text = "🔮 **برای پیش‌بندی نیاز به داده‌های بیشتری دارید.**"
        else:
            # Simple forecast based on current month
            days_passed = datetime.now().day
            days_in_month = 30
            projected = (analysis['total'] / days_passed) * days_in_month
            
            text = f"🔮 **پیش‌بندی ماه آینده**\n\n"
            text += f"📅 تا امروز: {days_passed} روز از ماه گذشته\n"
            text += f"💰 هزینه تاکنون: {analysis['total']:,} تومان\n"
            text += f"📈 میانگین روزانه: {int(analysis['total']/days_passed):,} تومان\n"
            text += f"🔮 پیش‌بندی کل ماه: {int(projected):,} تومان\n\n"
            
            if projected > analysis['total'] * 1.2:
                text += "⚠️ **هشدار:** روند فعلی نشان می‌دهد هزینه ماهانه شما افزایش خواهد یافت."
            else:
                text += "✅ **خبر خوب:** روند هزینه‌های شما ثابت است."
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("stats"),
            parse_mode="Markdown"
        )
    
    else:
        text = f"📊 **آمار {action}**\n\n(این بخش به زودی تکمیل می‌شود...)"
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("stats"),
            parse_mode="Markdown"
        )

async def handle_management_selection(query, data, user_id, context):
    """Management operations handler"""
    if data.startswith("export_"):
        export_type = data.replace("export_", "")
        
        if export_type == "excel_full":
            csv_data = AdvancedExpenseManager.export_to_csv(user_id)
            if csv_data:
                # Send as file
                file_buffer = io.BytesIO(csv_data.encode('utf-8'))
                file_buffer.name = f"expenses_{user_id}_{datetime.now().strftime('%Y%m%d')}.csv"
                
                await query.message.reply_document(
                    document=file_buffer,
                    caption="📤 **خروجی اکسل آماده شد!**\n\nفایل CSV حاوی تمام هزینه‌های شما.",
                    reply_markup=keyboard_manager.get_back_keyboard()
                )
                await query.delete_message()
            else:
                await query.edit_message_text(
                    "📭 **داده‌ای برای خروجی وجود ندارد!**\n\nلطفاً ابتدا هزینه‌ای ثبت کنید.",
                    reply_markup=menu.back_menu("management")
                )
        
        elif export_type == "csv":
            csv_data = AdvancedExpenseManager.export_to_csv(user_id)
            if csv_data:
                await query.edit_message_text(
                    f"📝 **خروجی CSV**\n\n```\n{csv_data[:1000]}\n```\n\n...\n\nبرای دریافت کامل فایل از 'خروجی اکسل' استفاده کنید.",
                    parse_mode="Markdown",
                    reply_markup=menu.back_menu("management")
                )
            else:
                await query.edit_message_text(
                    "📭 **داده‌ای برای خروجی وجود ندارد!**",
                    reply_markup=menu.back_menu("management")
                )
        
        else:
            await query.edit_message_text(
                f"📤 **خروجی {export_type}**\n\n(این قالب به زودی اضافه خواهد شد)",
                reply_markup=menu.back_menu("management")
            )
    
    elif data == "backup_create":
        backup = AdvancedExpenseManager.create_backup(user_id)
        
        await query.edit_message_text(
            f"✅ **پشتیبان‌گیری موفق**\n\n"
            f"📅 تاریخ: {backup['backup_date'][:10]}\n"
            f"📊 تعداد: {backup['total_records']} رکورد\n"
            f"💰 مجموع: {backup['total_amount']:,} تومان\n\n"
            f"پشتیبان شما ذخیره شد.",
            reply_markup=menu.back_menu("management"),
            parse_mode="Markdown"
        )
    
    elif data == "clean_data":
        await query.edit_message_text(
            "🗑️ **پاکسازی داده‌ها**\n\n"
            "آیا مطمئن هستید که می‌خواهید تمام داده‌های خود را پاک کنید؟\n\n"
            "⚠️ **توجه:** این عمل قابل بازگشت نیست!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بله، پاک کن", callback_data="confirm_clean")],
                [InlineKeyboardButton("❌ خیر، برگرد", callback_data="back_management")]
            ]),
            parse_mode="Markdown"
        )
    
    elif data == "system_stats":
        expenses = load_data(EXPENSES_FILE, [])
        users = load_data(USERS_FILE, {})
        
        text = f"📊 **آمار سیستم**\n\n"
        text += f"👥 تعداد کاربران: {len(users)}\n"
        text += f"📝 تعداد کل هزینه‌ها: {len(expenses)}\n"
        text += f"💰 مجموع کل هزینه‌ها: {sum(e['amount'] for e in expenses):,} تومان\n"
        
        # Most active user
        if expenses:
            user_activity = {}
            for e in expenses:
                user_activity[e['user_id']] = user_activity.get(e['user_id'], 0) + 1
            
            most_active = max(user_activity, key=user_activity.get)
            text += f"🏆 پرکاربرترین: کاربر {most_active[:8]} با {user_activity[most_active]} ثبت\n"
        
        await query.edit_message_text(
            text,
            reply_markup=menu.back_menu("management"),
            parse_mode="Markdown"
        )
    
    else:
        await query.edit_message_text(
            f"🔄 **مدیریت**\n\nقسمت '{data}' به زودی تکمیل می‌شود.",
            reply_markup=menu.back_menu("management"),
            parse_mode="Markdown"
        )

async def handle_advanced_search(query, context):
    """Advanced search handler"""
    await query.edit_message_text(
        "🔍 **جستجوی پیشرفته**\n\n"
        "برای جستجو یکی از فرمت‌های زیر را استفاده کنید:\n\n"
        "1. **جستجوی ساده:**\n"
        "   `غذا` - همه هزینه‌های مرتبط با غذا\n\n"
        "2. **جستجوی عددی:**\n"
        "   `>50000` - هزینه‌های بیشتر از ۵۰ هزار\n"
        "   `<20000` - هزینه‌های کمتر از ۲۰ هزار\n"
        "   `10000-50000` - بین ۱۰ تا ۵۰ هزار\n\n"
        "3. **جستجوی تاریخ:**\n"
        "   `2024-01` - دی ماه ۱۴۰۲\n"
        "   `2024-01-15` - ۱۵ دی ۱۴۰۲\n\n"
        "4. **ترکیبی:**\n"
        "   `غذا >50000 2024-01` - غذاهای بالای ۵۰ هزار در دی ماه\n\n"
        "لطفاً عبارت جستجو را وارد کنید:",
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_search_query"] = True

async def handle_back_button(query, data):
    """Back button handler"""
    target = data.replace("back_", "")
    
    if target == "main":
        await start_callback(query)
    
    elif target == "add":
        await query.edit_message_text(
            "🏷️ **انتخاب دسته‌بندی**\n\nلطفاً دسته هزینه را انتخاب کنید:",
            reply_markup=menu.categories_menu(),
            parse_mode="Markdown"
        )
    
    elif target == "reports":
        await query.edit_message_text(
            "📊 **گزارش‌ها و آمار پیشرفته**\n\nلطفاً نوع گزارش را انتخاب کنید:",
            reply_markup=menu.reports_menu(),
            parse_mode="Markdown"
        )
    
    elif target == "budgets":
        await query.edit_message_text(
            "🎯 **مدیریت بودجه پیشرفته**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=menu.budgets_menu(),
            parse_mode="Markdown"
        )
    
    elif target == "stats":
        await query.edit_message_text(
            "📈 **آمار و تحلیل پیشرفته**\n\nلطفاً نوع آمار را انتخاب کنید:",
            reply_markup=menu.stats_menu(),
            parse_mode="Markdown"
        )
    
    elif target == "management":
        await query.edit_message_text(
            "🔄 **مدیریت و تنظیمات**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=menu.management_menu(),
            parse_mode="Markdown"
        )
    
    else:
        await start_callback(query)

async def apply_coupon(query, context):
    """Apply discount code"""
    await query.edit_message_text(
        "🎁 **اعمال کد تخفیف**\n\n"
        "کد تخفیف: `FREEBOT100`\n\n"
        "✅ **تبریک! این ربات همیشه رایگان است!** 🎉\n\n"
        "نیازی به کد تخفیف ندارید. تمام امکانات رایگان در اختیار شماست.",
        reply_markup=keyboard_manager.get_main_keyboard(),
        parse_mode="Markdown"
    )

# ========== 🔄 Helper Functions ==========
async def start_callback(query):
    """Start robot through callback"""
    user = query.from_user
    welcome_text = f"""
🤖 **ربات مدیریت هوشمند هزینه‌ها**

سلام {user.first_name} 👋
به ربات مدیریت هزینه خوش آمدید!

📱 **از کیبورد پایین انتخاب کنید:**
"""
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=keyboard_manager.get_main_keyboard(),
        parse_mode="Markdown"
    )

# ========== 💬 Text Message Handler ==========
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Text message handler"""
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    
    # Check different states
    if context.user_data.get("awaiting_description"):
        await handle_expense_description(update, context, text)
    
    elif context.user_data.get("awaiting_custom_amount"):
        await handle_custom_amount(update, context, text)
    
    elif context.user_data.get("awaiting_new_category"):
        await handle_new_category(update, context, text)
    
    elif context.user_data.get("awaiting_search_query"):
        await handle_search_query(update, context, text)
    
    elif context.user_data.get("awaiting_coupon"):
        await handle_coupon_code(update, context, text)
    
    else:
        # Handle natural language input
        await handle_natural_input(update, context, text)

async def handle_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
    """Expense description handler"""
    if description.lower() in ["لغو", "cancel", "انصراف"]:
        await update.message.reply_text(
            "❌ عملیات ثبت هزینه لغو شد.",
            reply_markup=keyboard_manager.get_main_keyboard()
        )
        context.user_data.clear()
        return
    
    # Get saved data from context.user_data
    amount = context.user_data.get("selected_amount", 0)
    category = context.user_data.get("selected_category", "food")
    
    if amount <= 0:
        await update.message.reply_text(
            "❌ خطا در ثبت هزینه. لطفاً مجدداً تلاش کنید.",
            reply_markup=keyboard_manager.get_main_keyboard()
        )
        context.user_data.clear()
        return
    
    # Register expense
    category_name = AdvancedExpenseManager.get_category_name(f"cat_{category}")
    expense = AdvancedExpenseManager.add_expense(
        user_id=update.effective_user.id,
        amount=amount,
        category=category,
        description=description
    )
    
    # Response to user
    await update.message.reply_text(
        f"✅ **هزینه با موفقیت ثبت شد!**\n\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"🏷️ دسته: {category_name}\n"
        f"📝 توضیحات: {description if description else 'بدون توضیح'}\n"
        f"🕐 زمان: {expense['time']}",
        reply_markup=keyboard_manager.get_main_keyboard(),
        parse_mode="Markdown"
    )
    
    # Clear temporary data
    context.user_data.clear()

async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Custom amount handler"""
    amount = parse_amount(text)
    
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر! لطفاً عدد معتبر وارد کنید.\nمثال: 15000 یا 50هزار",
            reply_markup=keyboard_manager.get_cancel_keyboard()
        )
        return
    
    # Save amount and go to next step
    context.user_data["selected_amount"] = amount
    context.user_data.pop("awaiting_custom_amount", None)
    
    await update.message.reply_text(
        f"💰 **مبلغ وارد شد:** {amount:,} تومان\n\n"
        f"📝 لطفاً توضیحات هزینه را وارد کنید:\n"
        f"(می‌توانید خالی بگذارید یا از دکمه ❌ لغو استفاده کنید)",
        reply_markup=keyboard_manager.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    
    context.user_data["awaiting_description"] = True

async def handle_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """New category handler"""
    if len(text) > 20:
        await update.message.reply_text(
            "❌ نام دسته نباید بیشتر از ۲۰ کاراکتر باشد.\n\nلطفاً مجدداً وارد کنید:",
            reply_markup=keyboard_manager.get_cancel_keyboard()
        )
        return
    
    # Save new category
    context.user_data["new_category_name"] = text
    context.user_data.pop("awaiting_new_category", None)
    
    await update.message.reply_text(
        f"✅ **نام دسته ثبت شد:** {text}\n\n"
        f"💰 لطفاً مبلغ هزینه را انتخاب کنید:",
        reply_markup=menu.amounts_menu(),
        parse_mode="Markdown"
    )

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Search query handler"""
    user_id = str(update.effective_user.id)
    
    # Parse search query
    query_parts = text.split()
    search_text = ""
    min_amount = None
    max_amount = None
    date_filter = None
    
    for part in query_parts:
        if part.startswith('>'):
            try:
                min_amount = parse_amount(part[1:])
            except:
                pass
        elif part.startswith('<'):
            try:
                max_amount = parse_amount(part[1:])
            except:
                pass
        elif '-' in part and len(part) in [7, 10]:  # YYYY-MM or YYYY-MM-DD
            date_filter = part
        else:
            search_text += part + " "
    
    search_text = search_text.strip()
    
    # Perform search
    results = AdvancedExpenseManager.search_expenses(
        user_id=user_id,
        query=search_text,
        min_amount=min_amount,
        max_amount=max_amount,
        start_date=date_filter if date_filter and len(date_filter) == 10 else None
    )
    
    if not results:
        response = "🔍 **نتیجه‌ای یافت نشد!**\n\nلطفاً عبارت جستجوی خود را تغییر دهید."
    else:
        total = sum(r["amount"] for r in results)
        response = f"🔍 **نتایج جستجو ({len(results)} مورد)**\n\n"
        response += f"💰 مجموع: {total:,} تومان\n\n"
        
        for i, exp in enumerate(results[:10], 1):  # Show top 10
            cat_name = AdvancedExpenseManager.get_category_name(f"cat_{exp.get('category', 'unknown')}")
            response += f"{i}. {exp['amount']:,} تومان - {cat_name}\n"
            if exp.get('description'):
                response += f"   📌 {exp['description']}\n"
            response += f"   📅 {exp['date']} {exp['time']}\n\n"
        
        if len(results) > 10:
            response += f"... و {len(results) - 10} مورد دیگر\n"
    
    await update.message.reply_text(
        response,
        reply_markup=keyboard_manager.get_back_keyboard(),
        parse_mode="Markdown"
    )
    
    context.user_data.pop("awaiting_search_query", None)

async def handle_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Discount code handler"""
    coupon = text.strip().upper()
    
    if coupon == "FREEBOT100":
        response = "🎉 **تبریک!**\n\nاین ربات همیشه رایگان است! از تمام امکانات بهره‌مند شوید."
    else:
        response = f"❌ **کد تخفیف نامعتبر!**\n\nکد '{coupon}' معتبر نیست.\nکد صحیح: `FREEBOT100`"
    
    await update.message.reply_text(
        response,
        reply_markup=keyboard_manager.get_main_keyboard(),
        parse_mode="Markdown"
    )
    
    context.user_data.pop("awaiting_coupon", None)

async def handle_quick_expense(update: Update, text: str):
    """Quick expense registration"""
    # Find number in text
    numbers = re.findall(r'[\d,]+', text)
    if not numbers:
        return
    
    amount = parse_amount(numbers[0])
    if not amount:
        return
    
    description = re.sub(r'[\d,]+', '', text).strip()
    if not description:
        description = "ثبت سریع"
    
    # Simple category detection
    category = "food"  # Default
    
    # Register expense
    expense = AdvancedExpenseManager.add_expense(
        user_id=update.effective_user.id,
        amount=amount,
        category=category,
        description=description
    )
    
    await update.message.reply_text(
        f"✅ **ثبت سریع موفق!**\n\n"
        f"💰 {amount:,} تومان - {description}\n"
        f"🕐 {expense['time']}",
        reply_markup=keyboard_manager.get_main_keyboard(),
        parse_mode="Markdown"
    )

def parse_amount(amount_str):
    """Convert amount to number"""
    try:
        amount_str = str(amount_str)
        amount_str = amount_str.replace(",", "").replace(" ", "")
        
        # Handle Persian/English numbers
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        amount_str = amount_str.translate(persian_to_english)
        
        # Handle words like هزار, میلیون
        if "هزار" in amount_str:
            amount_str = amount_str.replace("هزار", "")
            multiplier = 1000
        elif "میلیون" in amount_str:
            amount_str = amount_str.replace("میلیون", "")
            multiplier = 1000000
        elif "میلیارد" in amount_str:
            amount_str = amount_str.replace("میلیارد", "")
            multiplier = 1000000000
        else:
            multiplier = 1
        
        # Extract numbers
        amount_str = re.sub(r'[^\d.]', '', amount_str)
        
        if not amount_str:
            return None
        
        amount = float(amount_str) * multiplier
        
        return int(amount) if amount.is_integer() else amount
    except:
        return None

# ========== 🚀 Main Robot Execution ==========
def main() -> None:
    """Start robot"""
    app = Application.builder().token(TOKEN).build()
    
    # Main commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("search", search_command))
    
    # Bottom keyboard handler - must come before generic text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_button))
    
    # Dropdown button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Add error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"Error occurred: {context.error}")
        try:
            if update and update.message:
                await update.message.reply_text(
                    "⚠️ **خطایی رخ داد!**\n\nلطفاً مجدد تلاش کنید.",
                    reply_markup=keyboard_manager.get_main_keyboard()
                )
        except:
            pass
    
    app.add_error_handler(error_handler)
    
    print("🤖 ربات مدیریت هزینه حرفه‌ای راه‌اندازی شد...")
    print("📱 منتظر کاربران هستیم...")
    print("🎯 ویژگی‌های فعال:")
    print("• ثبت سریع و هوشمند")
    print("• نمودارهای رنگی")
    print("• گزارش‌های پیشرفته")
    print("• جستجوی هوشمند")
    print("• پشتیبان‌گیری")
    print("• آمار و تحلیل")
    print("• مدیریت کامل")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Create data directory if not exists
    os.makedirs("data", exist_ok=True)
    
    # Initialize files if they don't exist
    for file in [EXPENSES_FILE, USERS_FILE, BUDGETS_FILE, INCOMES_FILE, CATEGORIES_FILE, BACKUP_FILE]:
        if not os.path.exists(file):
            save_data(file, [] if file.endswith('.json') else {})
    
    main()
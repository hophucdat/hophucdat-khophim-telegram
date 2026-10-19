import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F, types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import STREAM_BOT_TOKEN
from database import DatabaseService

router = Router()

# Khởi tạo các trạng thái FSM cho Admin
class AdminStates(StatesGroup):
    choosing_action = State()           # Chọn: Thêm phim mới hay Thêm tập phim cũ
    waiting_for_new_movie_title = State() # Nhập tên phim mới
    waiting_for_new_movie_desc = State()  # Nhập mô tả phim mới
    waiting_for_episode_num = State()     # Nhập số tập


# ==================== PHẦN 1: TÍNH NĂNG USER (XEM PHIM) ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Kho Phim", callback_data="open_movie_catalog")
    builder.adjust(1)

    await message.answer(
        "👋 Chào mừng bạn đến với **Kho Phim Của Đồng Đồng**!\n\n"
        "👉 Bấm vào nút bên dưới để mở danh sách phim hiện có:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "open_movie_catalog")
async def show_movie_catalog(callback: types.CallbackQuery):
    movies = DatabaseService.get_all_movies()

    if not movies:
        await callback.message.edit_text(
            "⚠️ Hiện tại chưa có bộ phim nào trong Kho Phim!",
            reply_markup=None
        )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for movie in movies:
        builder.button(
            text=f"🎥 {movie['title']}", 
            callback_data=f"view_movie:{movie['movie_id']}"
        )
    builder.adjust(1)

    await callback.message.edit_text(
        "📚 **DANH SÁCH PHIM HIỆN CÓ**\nVui lòng chọn bộ phim bạn muốn xem:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_movie:"))
async def view_movie_details(callback: types.CallbackQuery):
    movie_id = int(callback.data.split(":")[1])
    movie = DatabaseService.get_movie_by_id(movie_id)

    if not movie:
        await callback.answer("❌ Không tìm thấy thông tin bộ phim này!", show_alert=True)
        return

    episodes = DatabaseService.get_episodes_by_movie_id(movie_id)

    builder = InlineKeyboardBuilder()
    if episodes:
        for ep in episodes:
            builder.button(
                text=f"▶️ Tập {ep['episode_num']}", 
                callback_data=f"play_ep:{ep['episode_id']}"
            )
        builder.adjust(3)
    
    builder.row(types.InlineKeyboardButton(text="🔙 Quay lại Kho Phim", callback_data="open_movie_catalog"))

    text_content = (
        f"🎬 **{movie['title']}**\n\n"
        f"📝 **Mô tả:** {movie.get('description') or 'Chưa có mô tả'}\n\n"
        f"📌 **Danh sách tập:** " + (f"(Tổng {len(episodes)} tập)" if episodes else "*(Chưa có tập nào được cập nhật)*")
    )

    await callback.message.edit_text(
        text_content,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("play_ep:"))
async def play_episode(callback: types.CallbackQuery):
    episode_id = int(callback.data.split(":")[1])
    episode = DatabaseService.get_episode_by_id(episode_id)

    if not episode:
        await callback.answer("❌ Tập phim này không tồn tại hoặc đã bị xóa!", show_alert=True)
        return

    movie = DatabaseService.get_movie_by_id(episode['movie_id'])
    title = movie['title'] if movie else "Phim"

    await callback.answer("🚀 Đang gửi video, vui lòng đợi trong giây lát...")
    
    await callback.message.answer_video(
        video=episode['telegram_file_id'],
        caption=f"🎬 **{title}** - **Tập {episode['episode_num']}**\n\n🍿 Chúc bạn xem phim vui vẻ!",
        parse_mode="Markdown"
    )


# ==================== PHẦN 2: TÍNH NĂNG ADMIN NÂNG CẤP ====================

ADMIN_IDS = [8143622804] # ID Telegram của bạn

@router.message(F.video)
async def handle_admin_video(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⚠️ Bạn không có quyền sử dụng tính năng này!")
        return

    # Lưu file_id vào trạng thái tạm thời
    file_id = message.video.file_id
    await state.update_data(telegram_file_id=file_id)

    # Hiển thị bảng lựa chọn: Tạo phim mới hay thêm vào phim cũ
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Tạo Phim Mới", callback_data="admin_action:new_movie")
    builder.button(text="📂 Thêm Vào Phim Đã Có", callback_data="admin_action:existing_movie")
    builder.adjust(1)

    await message.answer(
        "📥 **Đã nhận video thành công!**\nBạn muốn xử lý video này như thế nào?",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.choosing_action)

@router.callback_query(AdminStates.choosing_action, F.data.startswith("admin_action:"))
async def process_admin_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]

    if action == "new_movie":
        await callback.message.edit_text(
            "🎬 Vui lòng gửi **Tên bộ phim mới** bằng tin nhắn văn bản:",
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.waiting_for_new_movie_title)
    elif action == "existing_movie":
        movies = DatabaseService.get_all_movies()
        if not movies:
            await callback.message.edit_text("⚠️ Kho phim đang trống, vui lòng chọn **Tạo Phim Mới**!")
            await state.clear()
            await callback.answer()
            return

        builder = InlineKeyboardBuilder()
        for movie in movies:
            builder.button(text=f"🎥 {movie['title']}", callback_data=f"admin_pick_movie:{movie['movie_id']}")
        builder.adjust(1)

        await callback.message.edit_text(
            "📚 Chọn bộ phim bạn muốn thêm tập vào:",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    await callback.answer()

# --- Luồng 1: Tạo Phim Mới Từ A-Z ---
@router.message(AdminStates.waiting_for_new_movie_title)
async def process_new_movie_title(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    movie_title = message.text.strip()
    await state.update_data(movie_title=movie_title)

    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Bỏ qua mô tả", callback_data="skip_movie_desc")
    
    await message.answer(
        f"📝 Bạn đã đặt tên phim là: **{movie_title}**\n\n"
        "Bây giờ hãy nhập **Mô tả/Giới thiệu ngắn** cho phim này (hoặc bấm nút bên dưới để bỏ qua):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_new_movie_desc)

@router.callback_query(AdminStates.waiting_for_new_movie_desc, F.data == "skip_movie_desc")
async def skip_description(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(movie_desc="")
    await callback.message.edit_text(
        "🔢 Vui lòng gửi **số tập** của video này (ví dụ: `1`):",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_episode_num)
    await callback.answer()

@router.message(AdminStates.waiting_for_new_movie_desc)
async def process_new_movie_desc(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await state.update_data(movie_desc=message.text.strip())
    await message.answer("🔢 Vui lòng gửi **số tập** của video này (ví dụ: `1`):", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_episode_num)

# --- Luồng 2: Chọn Phim Cũ ---
@router.callback_query(F.data.startswith("admin_pick_movie:"))
async def process_pick_existing_movie(callback: types.CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split(":")[1])
    await state.update_data(movie_id=movie_id)

    await callback.message.edit_text(
        "🔢 Vui lòng gửi **số tập** bạn muốn thêm vào phim này (ví dụ: `2`, `3`...):",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_episode_num)
    await callback.answer()

# --- Bước Cuối: Lưu vào Database (Dùng chung cho cả 2 luồng) ---
@router.message(AdminStates.waiting_for_episode_num)
async def save_episode_final(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.text.isdigit():
        await message.answer("⚠️ Vui lòng chỉ nhập số tập hợp lệ dưới dạng số (ví dụ: `1`, `2`)!")
        return

    episode_num = int(message.text)
    data = await state.get_data()
    telegram_file_id = data.get("telegram_file_id")
    movie_id = data.get("movie_id")
    movie_title = data.get("movie_title")
    movie_desc = data.get("movie_desc")

    try:
        # Nếu chưa có movie_id nhưng có tên phim mới, tiến hành tạo phim mới qua DatabaseService
        if not movie_id and movie_title:
            movie_id = DatabaseService.create_movie(
                title=movie_title,
                description=movie_desc,
                is_vip_only=False
            )

        if not movie_id:
            raise Exception("Không thể xác định hoặc tạo mới thông tin bộ phim.")

        # Lưu tập phim vào bảng episodes
        DatabaseService.add_episode(movie_id, episode_num, telegram_file_id)
        
        target_name = movie_title if movie_title else f"ID: {movie_id}"
        await message.answer(
            f"🎉 **Thành công tuyệt đối!**\n\n"
            f"🎬 Phim: `{target_name}`\n"
            f"📌 Tập: `{episode_num}` đã được đưa lên hệ thống!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Lỗi khi lưu vào database: {str(e)}")

    await state.clear()


# ==================== KHỞI ĐỘNG BOT ====================
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    if not STREAM_BOT_TOKEN:
        print("❌ Lỗi: Thiếu TOKEN trong file .env!")
        return

    bot = Bot(token=STREAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("🚀 Bot quản lý kho phim nâng cao đang chạy...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import tkinter as tk
from tkinter import font
from translate import Translator
import time

class RealtimeTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI TOEIC Translator - Chạy liên tục (CTranslate2)")
        self.root.geometry("900x500")
        
        # Cấu hình grid để tự căn chỉnh rộng dài
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        
        # Biến trạng thái
        self.status_var = tk.StringVar()
        self.status_var.set("⏳ Đang tải model CTranslate2 vào RAM... Vui lòng đợi!")
        
        # Nhãn Trạng thái phía trên
        self.lbl_status = tk.Label(self.root, textvariable=self.status_var, font=("Arial", 11, "bold"), fg="#d35400")
        self.lbl_status.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Ô nhập liệu tiếng Anh (Trái)
        self.txt_en = tk.Text(self.root, font=("Consolas", 14), wrap="word", bd=2, relief="groove")
        self.txt_en.grid(row=1, column=0, padx=(15, 5), pady=10, sticky="nsew")
        self.txt_en.bind("<KeyRelease>", self.on_text_change)
        
        # Ô xuất kết quả tiếng Việt (Phải)
        self.txt_vi = tk.Text(self.root, font=("Arial", 14), wrap="word", bg="#f7f9fc", bd=2, relief="groove", state="normal")
        self.txt_vi.grid(row=1, column=1, padx=(5, 15), pady=10, sticky="nsew")
        
        self.translator = None
        self._timer = None
        
        # Khởi chạy tải model sau khi GUI hiện lên (tránh treo cửa sổ lúc mới bật)
        self.root.after(100, self.load_ai_model)
        
    def load_ai_model(self):
        try:
            self.translator = Translator()
            self.status_var.set("✅ Model Đã Sẵn Sàng (Chạy 24/24). Hãy gõ văn bản tiếng Anh vào ô bên trái!")
            self.lbl_status.config(fg="#27ae60")
        except Exception as e:
            self.status_var.set(f"❌ Lỗi khởi tạo model: {e}")
            self.lbl_status.config(fg="#c0392b")
            
    def on_text_change(self, event):
        # Bắt sự kiện bàn phím. Nếu hủy bộ hẹn giờ cũ (để chống spam dịch khi đang gõ liên tiếp).
        if self._timer is not None:
            self.root.after_cancel(self._timer)
        # Chỉ tự động dịch sau khi người dùng dừng gõ 500ms
        self._timer = self.root.after(500, self.perform_translation)
        
    def perform_translation(self):
        if not self.translator:
            return
            
        text = self.txt_en.get("1.0", tk.END).strip()
        if not text:
            self.txt_vi.delete("1.0", tk.END)
            self.status_var.set("✅ Model Đã Sẵn Sàng (Chạy 24/24). Hãy gõ tiếng Anh vào ô bên trái.")
            return
            
        start_time = time.time()
        
        # Check xem có phải là từ đơn không (không có khoảng trắng)
        lines = text.split("\n")
        is_single_word = (len(lines) == 1 and " " not in text.strip())
        
        if len(lines) > 1:
            results = self.translator.translate_batch(lines)
            res_text = "\n".join(results)
        else:
            base_trans = self.translator.translate(text)
            res_text = base_trans
            
            if is_single_word:
                # Xử lý format model fine-tuned (word / pos / pron / mean)
                parts = [p.strip() for p in base_trans.split(" / ")]
                if len(parts) >= 3:
                    m_pos = parts[1]
                    m_pron = parts[2]
                    m_mean = " / ".join(parts[3:]) if len(parts) > 3 else ""
                    # Dùng từ gốc (text) thay cho từ model sinh ra (parts[0]) để tránh ảo giác
                    res_text = f"{text.strip().capitalize()} ({m_pos})\n\n{m_pron}\n\n{m_mean.capitalize()}"
                else:
                    # Nếu model không ra format từ điển, thử dùng Dictionary API làm fallback
                    import urllib.request
                    import urllib.parse
                    import json
                    word = text.strip()
                    try:
                        req = urllib.request.Request(
                            f'https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}', 
                            headers={'User-Agent': 'Mozilla/5.0'}
                        )
                        with urllib.request.urlopen(req, timeout=2) as u:
                            data = json.loads(u.read().decode())
                            entry = data[0]
                            phonetic = entry.get('phonetic', '')
                            if not phonetic and entry.get('phonetics'):
                                for p in entry['phonetics']:
                                    if p.get('text'):
                                        phonetic = p['text']
                                        break
                            pos_list = []
                            for m in entry.get('meanings', []):
                                if m.get('partOfSpeech'):
                                    pos_list.append(m['partOfSpeech'])
                            
                            pos_str = ""
                            if pos_list:
                                pos_map = {"noun": "n", "adjective": "adj", "verb": "v", "adverb": "adv", "pronoun": "pron", "preposition": "prep", "conjunction": "conj"}
                                mapped = [pos_map.get(pos, pos[:3]) for pos in list(dict.fromkeys(pos_list))]
                                pos_str = f"({', '.join(mapped)})"
                                
                            header = f"{word.capitalize()} {pos_str}".strip()
                            phonetic_part = f"\n\n{phonetic}\n\n" if phonetic else "\n\n"
                            res_text = f"{header}{phonetic_part}{base_trans.capitalize()}"
                    except Exception:
                        pass
            
        ms = (time.time() - start_time) * 1000
        
        # Cập nhật kết quả lên UI
        self.txt_vi.delete("1.0", tk.END)
        self.txt_vi.insert(tk.END, res_text)
        
        # Hiển thị tốc độ
        source = "Dùng Trí Tuệ Nhân Tạo" if ms > 15 else "Lấy từ Cache Siêu Tốc"
        self.status_var.set(f"⚡ Đã dịch xong! (Tốc độ: {ms:.1f} ms) - {source}")

if __name__ == "__main__":
    root = tk.Tk()
    
    # Ràng buộc phím Esc để thoát ngầm định
    root.bind("<Escape>", lambda e: root.quit())
    
    app = RealtimeTranslatorApp(root)
    root.mainloop()

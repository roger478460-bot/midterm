import sys
import os
import pygame
import requests

API_BASE_URL = "http://127.0.0.1:8000"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)    # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色

pygame.init()
WIDTH, HEIGHT = 700, 650  # 擴寬以容納側邊欄
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.hard_mode = False
        self.message = "Press ENTER to submit, R to restart, H for Hard Mode"
        self.history = []  # 歷史猜測紀錄
        self.stats = {"total": 0, "wins": 0, "win_rate": 0}
        self.start_new_game()

    def start_new_game(self):
        """向 FastAPI 伺服器請求建立新的一局"""
        try:
            payload = {"hard_mode": self.hard_mode}
            res = requests.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.stats = data.get("stats", self.stats)
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.history = []
                mode_str = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! Mode: {mode_str}"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def submit_guess(self):
        """將當前行單字發送至 FastAPI 驗證"""
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                self.stats = data.get("stats", self.stats)
                
                # 記錄歷史
                self.history.append(guess_word)

                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        target = data.get("target_word", "UNKNOWN")
                        self.message = f"Game Over! The word was {target}. Press R."
                        self.game_over = True
                    else:
                        tries_left = 6 - self.row
                        self.message = f"Keep guessing! ({tries_left} tries left)"
            else:
                # 任務二：字典庫驗證錯誤處理，身體不消耗猜測次數
                err_detail = res.json().get("detail", "Error")
                if err_detail == "Word not in dictionary":
                    self.message = "Not in word list!"
                elif "Hard Mode" in err_detail:
                    self.message = err_detail
                else:
                    self.message = err_detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_r:
            self.start_new_game()
            return

        # 任務四：按下 H 鍵切換 Hard Mode
        if event.key == pygame.K_h:
            self.hard_mode = not self.hard_mode
            self.start_new_game()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        margin_x, margin_y = 50, 50
        box_size = 50
        gap = 8

        # 1. 繪製 6x5 網格
        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 2. 任務三：繪製右側側邊欄（歷史紀錄與勝率）
        pygame.draw.line(surface, (80, 80, 80), (410, 20), (410, 580), 2)
        
        # 顯示勝率統計
        stat_text = f"Total: {self.stats['total']} | Wins: {self.stats['wins']} | Win Rate: {self.stats['win_rate']}%"
        stat_surface = small_font.render(stat_text, True, COLOR_TEXT)
        surface.blit(stat_surface, (430, 30))

        # 顯示歷史猜測字串
        history_title = small_font.render("Guess History:", True, COLOR_TEXT)
        surface.blit(history_title, (430, 70))
        for idx, word in enumerate(self.history):
            w_surface = small_font.render(f"{idx+1}. {word}", True, COLOR_TEXT)
            surface.blit(w_surface, (430, 100 + idx * 30))

        # 任務四：顯示目前模式於右上角
        mode_text = f"Mode: {'HARD' if self.hard_mode else 'Normal'}"
        mode_surface = small_font.render(mode_text, True, (255, 100, 100) if self.hard_mode else (100, 255, 100))
        surface.blit(mode_surface, (WIDTH - 130, 15))

        # 3. 畫底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2, HEIGHT - 30))
        surface.blit(msg_surface, msg_rect)


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()

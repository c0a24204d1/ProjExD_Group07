import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/hart.png"), 0, 0.015)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): img,
            (0, -1):img,
            (-1, -1):img,
            (-1, 0): img0,  # 左
            (-1, +1): img,
            (0, +1): img,
            (+1, +1): img,
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.status = "normal"  # ハートの状態を設定(通常状態)
        self.hyper_life = 0  # 無敵時間の設定

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/hartbreak.png"), 0, 0.08)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            # self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)
        if self.status == "hyper":  # 無敵状態になっている場合
            self.hyper_life -= 10  # 無敵時間は10フレーム減らす
            if self.hyper_life <= 0:  # 無敵時間が0になる場合 +
                self.status = "normal"  # 通常状態にする

    def get_rect(self) -> pg.Rect:
        return self.rect

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()  
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class BossBeam(pg.sprite.Sprite):
    """
    ボスが発射するビーム
    """
    def __init__(self, boss_rect: pg.Rect, direction: tuple[float, float]):
        super().__init__()
        angle = math.degrees(math.atan2(-direction[1], direction[0]))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1)
        self.rect = self.image.get_rect()
        self.rect.center = boss_rect.center  # ボスの中心から発射

        self.vx, self.vy = direction
        self.speed = 7

    def update(self):
        self.rect.move_ip(self.vx * self.speed, self.vy * self.speed)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam2(pg.sprite.Sprite):
    """
    ビームに関するクラス2
    """
    imgs = [pg.image.load("fig/beam.png")]  # ビーム画像のsurface
    def __init__(self):
        """
        ビームに画像surfaceを生成する
        """
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), -90, 3)  # 画像の角度と倍率を変えて生成する
        self.image.set_colorkey((0, 0, 0))  # 四隅の黒を透明化する
        self.rect = self.image.get_rect()  # ビーム画像をrect
        self.rect.center = random.randint(0, WIDTH), 0  # 上側からランダムな位置に出現
        self.x, self.y = 0, +10  # x座標とy座標の進む速さ 

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.x, self.y)  # ビームの速度に応じて移動させる
        if self.rect.bottom > HEIGHT:  # 画面の底に着いた場合
            self.kill()  # ビームを消す


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class BossBall(pg.sprite.Sprite): 
    """
    ボスが発射する即死球の設定
    引数1 boss_rct ボスのRect（中心から弾を出す）
    引数2 bird 操作しているキャラの位置に向けて発射するための参照
    """ 
    def __init__(self, boss_rct: pg.Rect, bird: Bird):
        super().__init__()
        radball = 15
        self.image = pg.Surface((2*radball, 2*radball))
        pg.draw.circle(self.image, (0, 0, 0), (radball, radball), radball)
        self.image.set_colorkey((0, 0, 0))
        pg.draw.circle(self.image, (255, 0, 0), (radball, radball), radball, 5)
        self.rect = self.image.get_rect(center=boss_rct.center)
        angle = random.uniform(0,360)
        self.vx = math.cos(math.radians(angle))
        self.vy = math.sin(math.radians(angle))
        self.speed = 4
        self.frames = 0

    def update(self):
        """ 
        移動・跳ね返り処理・寿命処理を行う 
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        yoko, tate = check_bound(self.rect)
        if not yoko:
            self.vx *= -1  
        if not tate:
            self.vy *= -1  
        self.frames += 1
        if self.frames > 3000: # 3000フレーム後削除される。
            self.kill()         


class HP:
    """
    プレイヤーHP
    base=30
    """
    def __init__(self,Numhp):
        self.font = pg.font.Font(None, 30)
        self.color = (255, 255, 0)
        self.value = Numhp
        self.maxhp = self.value
        self.txt = self.font.render(f"HP: {self.value}/{self.maxhp}", 0, self.color)
        self.image = pg.Surface((self.maxhp*2, 20))
        pg.draw.rect(self.image,(255, 255, 0),(0, 0, self.maxhp*2, 20))
        self.image.set_alpha(255)
        self.rect = self.image.get_rect()
        self.rect2 = self.txt.get_rect()
        self.rect.center = WIDTH//2, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = pg.Surface((self.maxhp*2, 20))
        pg.draw.rect(self.image,(255, 255, 0),(0, 0, self.value*2, 20))
        self.image.set_alpha(255)
        self.txt = self.font.render(f"HP: {self.value}/{self.maxhp}", 0, self.color)
        screen.blit(self.image, self.rect)
        screen.blit(self.txt, [WIDTH//2-140, HEIGHT-60])


class BossHP:
    """
    ボスのHP
    base=1200
    """
    def __init__(self):
        self.font = pg.font.Font(None, 30)
        self.color = (255, 0, 0)
        self.value = 1200
        self.txt = self.font.render(f"HP: {self.value}/1200", 0, self.color)
        self.image = pg.Surface((120,20))
        pg.draw.rect(self.image,(255,0,0),(0,0,120,20))
        self.image.set_alpha(255)
        self.rect = self.image.get_rect()
        self.rect2 = self.txt.get_rect()
        self.rect.center = WIDTH//2, HEIGHT-600

    def update(self, screen: pg.Surface):
        self.image = pg.Surface((120,20))
        pg.draw.rect(self.image,(255,0,0),(0,0,self.value//10,20))
        self.image.set_alpha(255)
        self.txt = self.font.render(f"HP: {self.value}/1200", 0, self.color)
        screen.blit(self.image, self.rect)
        screen.blit(self.txt,[WIDTH//2-240,HEIGHT-610])


class Slash(pg.sprite.Sprite):
    """
    斬撃エフェクト
    """
    def __init__(self, life):
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/flash-effect.gif"), 0, 0.3)
        self.image.set_alpha(255)  # 透明度
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH//2,HEIGHT//2-180
        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()  # 以下衝突検知・破壊処理


class Start:
    """
    起動時の画面に関するクラス
    """
    def __init__(self):
        self.running = True
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        self.gamemode = "normal"

    def show_start_screen(self):
        """
        起動時の画面を表示する
        黒背景、文字
        """
        self.black = pg.Surface((WIDTH,HEIGHT))
        self.black.fill((0,0,0))
        self.rect = self.black.get_rect()
        self.screen.blit(self.black,(0,0))
        self.draw_text("UNDERKOKATON",96,(255,255,255),WIDTH/2,HEIGHT/2)
        self.draw_text("Press Space to play",36,(255,255,255),WIDTH/2,HEIGHT/2+120)
        pg.display.flip()
        self.wait_for_key()

    def draw_text(self, text:str, size:int, color:tuple, x:float, y:float):
        """
        テキストを表示するための関数
        """
        font = pg.font.SysFont(None, size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        text_rect.midtop = (x, y)
        self.screen.blit(text_surface, text_rect)
        
    def wait_for_key(self):
        """
        スペースキー入力があるまで動作を停止する
        hキー入力でハードモード化（仮）
        """
        pg.mixer.music.load("fig/Battle_standby.mp3")
        pg.mixer.music.play(-1)
        while True:
            self.clock.tick(50)  # 処理落ち防止
            for event in pg.event.get():
                if event.type == pg.QUIT:  # 右上の×が押されたら
                    self.running = False  
                    pg.mixer.music.stop()
                    return
                if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:  # スペースキーが押されたら
                    pg.mixer.music.stop()
                    return
                elif event.type == pg.KEYDOWN and event.key == pg.K_h:
                    self.gamemode = "hard"
                    return
                elif event.type == pg.KEYDOWN and event.key == pg.K_e:
                    self.gamemode = "easy"
                    return
                elif event.type == pg.KEYDOWN and event.key == pg.K_x:
                    self.gamemode = "X"
                    return
                    
def main():
    pg.display.set_caption("UNDERKOKATON")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    # hp = HP()
    pg.mixer.init()
    beam_se = pg.mixer.Sound("fig/beam.wav")
    bosshp = BossHP()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    boss_beams =pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    sla = pg.sprite.Group()    
    bossballs = pg.sprite.Group() # 即死球を管理するグループ
    beam_b2 = pg.sprite.Group()  # 上から降ってくるビーム用のグループオブジェクトを生成

    tmr = 0
    beam_pattern = 0  # 0:3方向, 1:5方向
    muteki=0
    PLwaza=0
    namida=0
    At = 60
    clock = pg.time.Clock()
    go_img=pg.Surface((WIDTH,HEIGHT))
    pg.draw.rect(go_img,(0, 0, 0),(0, 0, WIDTH,HEIGHT))
    go_img.set_alpha(255)
    go_rct = go_img.get_rect()
    go_rct.center=WIDTH//2,HEIGHT//2

    boss_img = pg.transform.rotozoom(pg.image.load(f"fig/7.png"), 0, 3)
    boss_rct = boss_img.get_rect()
    boss_rct.center = WIDTH//2,HEIGHT//2-180
    start = Start()
    start.show_start_screen()
    hp=HP(50)
    if start.running is not True:
        return
    if start.gamemode is "hard":
        hp.value = 30
        hp.maxhp = 30
    if start.gamemode is "easy":
        hp.value = 80
        hp.maxhp = 80
        At = 100
    if start.gamemode is "X":
        hp.value = 1
        hp.maxhp = 1
    pg.mixer.music.load("fig/bossbgm.mp3")  # 戦闘BGMの設定
    pg.mixer.music.play(-1)  # 戦闘BGMを無限ループで再生
    pg.mixer.music.set_volume(0.5)  # 戦闘BGMの音量を半分にする

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE and PLwaza >=1:
                bosshp.value -= At
                PLwaza=0
                boss_img = pg.transform.rotozoom(pg.image.load(f"fig/8.png"), 0, 3)
                namida=50
                sla.add(Slash(50))
                
        screen.blit(bg_img, [0, 0])

        if tmr % 100 == 0:  # 200フレームに1回，敵機を出現させる
            beam_se.play()  # 効果音を鳴らす（beam.wav）
            if beam_pattern == 0:
                directions = [(-1, 1), (0, 1), (1, 1)]  # ↙ ↓ ↘
            else:
                directions = [(-1, 1), (-0.5, 1), (0, 1), (0.5, 1), (1, 1)]  # 5方向

            for d in directions:
                norm = math.sqrt(d[0]**2 + d[1]**2)
                dir_vec = (d[0]/norm, d[1]/norm)
                boss_beams.add(BossBeam(boss_rct, dir_vec))
            beam_pattern = 1 - beam_pattern  # 交互切り替え
    
        if tmr % 10 == 0:  # 10フレームごとにビーム(ボス側)が発射
            beam_b2.add(Beam2())

        if tmr%300 == 0 and tmr!=0:
            PLwaza=1

        for emy in emys:
            if emy.state is "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))
        if start.gamemode is "easy":
            if tmr % 400 == 0: # 400フレームに1回,即死球を出現させる。
                bossballs.add(BossBall(boss_rct, bird))
        elif start.gamemode is "X":
            if tmr % 40 == 0: # 40フレームに1回,即死球を出現させる。
                bossballs.add(BossBall(boss_rct, bird))
        else:
            if tmr % 100 == 0: # 100フレームに1回,即死球を出現させる。
                bossballs.add(BossBall(boss_rct, bird))

        screen.blit(go_img,go_rct)
        
        for bomb in pg.sprite.spritecollide(bird, beam_b2, True):  # ハートと衝突したビームリスト
            if muteki<0:
                hp.value -= 3
                muteki=30
            else:
                continue
        for beam in pg.sprite.spritecollide(bird, boss_beams, True):
            if muteki<0:
                hp.value -= 2  # HPを5減らす
                muteki=30
            else:
                continue
        
        if muteki>0:
            bird.image = pg.transform.laplacian(bird.image)
        elif PLwaza>=1:
            bird.image = pg.transform.rotozoom(pg.image.load(f"fig/hartSP.png"), 0, 0.015)
        else:
            bird.image = pg.transform.rotozoom(pg.image.load(f"fig/hart.png"), 0, 0.015)

        if hp.value<=0:
            pg.mixer.music.stop()  # 戦闘BGMの停止
            hp.value=0
            bird.change_img(8, screen)
            fonto=pg.font.Font(None,80)
            txt = fonto.render("Game Over",True, (255,0,0))
            screen.blit(txt,[WIDTH//2-150,HEIGHT//2])
            hp.update(screen)
            pg.display.update()
            time.sleep(2)                
            return  # gameover
        
        if bosshp.value<=0:
            pg.mixer.music.stop()  # 戦闘BGMの停止
            bosshp.value=0
            fonto=pg.font.Font(None,80)
            txt = fonto.render("Game Clear",True, (255,255,0))
            screen.blit(txt,[WIDTH//2-150,HEIGHT//2])
            hp.update(screen)
            pg.display.update()
            time.sleep(2)                
            return  # gameclear
        
        if namida<0:
            boss_img = pg.transform.rotozoom(pg.image.load(f"fig/7.png"), 0, 3)
        
        for ball in pg.sprite.spritecollide(bird, bossballs, True):  # 衝突したさいの即死球リスト
            if muteki<0:
                hp.value=0 # 自分のHPを0にする。
            else:
                continue

        for beam in pg.sprite.spritecollide(bird, boss_beams, True):
            hp.value -= 2  # HPを5減らす
            if hp.value <= 0:
                bird.change_img(8, screen)
                hp.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        screen.blit(boss_img, boss_rct)
        bird.update(key_lst, screen)
        beams.update
        beams.draw(screen)
        boss_beams.update()
        boss_beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        bossballs.update() # 即死球を更新        
        bossballs.draw(screen) # 即死球を画面に描画    
        exps.update()
        exps.draw(screen)
        hp.update(screen)
        bosshp.update(screen)
        if tmr % 100 == 0:
            directions = [(-1, 1), (0, 1), (1, 1)]  # ↙ ↓ ↘
            for d in directions:
                norm = math.sqrt(d[0] ** 2 + d[1] ** 2)
                dir_vec = (d[0] / norm, d[1] / norm)
                boss_beams.add(BossBeam(boss_rct, dir_vec))
        beam_b2.update()
        beam_b2.draw(screen)
        sla.update()
        sla.draw(screen)
        pg.display.update()
        tmr += 1
        muteki-=1
        namida-=1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    pg.mixer.init()
    main()
    pg.quit()
    sys.exit()

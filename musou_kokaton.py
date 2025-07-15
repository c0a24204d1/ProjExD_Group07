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
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/hart.png"), 0, 0.02)
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
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)
        if self.status == "hyper":  # 無敵状態になっている場合
            self.hyper_life -= 10  # 無敵時間は10フレーム減らす
            if self.hyper_life <= 0:  # 無敵時間が0になる場合 +
                self.status = "normal"  # 通常状態にする


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


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class HP:
    """
    プレイヤーHP
    base=30
    """
    def __init__(self):
        self.font = pg.font.Font(None, 30)
        self.color = (255, 255, 0)
        self.value = 30
        self.txt = self.font.render(f"HP: {self.value}/30", 0, self.color)
        self.image = pg.Surface((60, 20))
        pg.draw.rect(self.image,(255, 255, 0),(0, 0, 60, 20))
        self.image.set_alpha(255)
        self.rect = self.image.get_rect()
        self.rect2 = self.txt.get_rect()
        self.rect.center = WIDTH//2, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = pg.Surface((60, 20))
        pg.draw.rect(self.image,(255, 255, 0),(0, 0, self.value*2, 20))
        self.image.set_alpha(255)
        self.txt = self.font.render(f"HP: {self.value}/30", 0, self.color)
        screen.blit(self.image, self.rect)
        screen.blit(self.txt, [WIDTH//2-140, HEIGHT-60])


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = HP()
    
    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    beam_b2 = pg.sprite.Group()  # 上から降ってくるビーム用のグループオブジェクトを生成

    tmr = 0
    clock = pg.time.Clock()
    go_img=pg.Surface((WIDTH,HEIGHT))
    pg.draw.rect(go_img,(0,0,0),(0,0,WIDTH,HEIGHT))
    go_img.set_alpha(255)
    go_rct = go_img.get_rect()
    go_rct.center=WIDTH//2,HEIGHT//2

    boss_img = pg.transform.rotozoom(pg.image.load(f"fig/7.png"), 0, 3)
    boss_rct = boss_img.get_rect()
    boss_rct.center = WIDTH//2,HEIGHT//2-180
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())
        
        if tmr % 10 == 0:  # 10フレームごとにビーム(ボス側)が発射
            beam_b2.add(Beam2())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        screen.blit(go_img,go_rct)
        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # ハートと衝突した爆弾リスト
            if bird.status == "normal":  # 通常状態の場合
                score.value -= 5  # 5ダメージ受ける(HPから5減らす)
                if score.value > 0:  # HPが残っている場合
                    bird.status = "hyper"  # 無敵状態用に切り替える
                    bird.hyper_life = 500  # 500フレームを与える

                if score.value <= 0:
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    return
        
        for beam2 in pg.sprite.spritecollide(bird, beam_b2, True):  # ハートと衝突したビームリスト
            if bird.status == "normal":  # 通常状態の場合
                score.value -= 4  # 4ダメージ受ける(HPから4減らす)
                if score.value > 0:  # HPが残っている場合
                    bird.status = "hyper"  # 無敵状態用に切り替える
                    bird.hyper_life = 500  # 500フレームを与える
                
                if score.value <= 0:  # 0以下の場合
                    bird.change_img(8, screen)  # ハートが割れる画像に変える
                    score.update(screen)
                    pg.display.update()
                    time.sleep(2)  # 2秒間止まる
                    return

        screen.blit(boss_img, boss_rct)
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        beam_b2.update()
        beam_b2.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()

import math
import os
import random
import sys
import time
import pygame as pg


WIDTH, HEIGHT = 1000, 600  # ゲームウィンドウの幅，高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct:pg.Rect) -> tuple[bool, bool]:
    """
    Rectの画面内外判定用の関数
    引数：こうかとんRect，または，爆弾Rect，またはビームRect
    戻り値：横方向判定結果，縦方向判定結果（True：画面内／False：画面外）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:  # 横方向のはみ出し判定
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:  # 縦方向のはみ出し判定
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
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.high_speed = 20  # feature1
        self.high = False

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
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
        if pg.key.get_mods() & pg.KMOD_LSHIFT:  # 左Shiftキーが押されているか確認
            self.speed = self.high_speed  # 高速化
            self.high = True
        else:
            self.speed = 10
            self.high = False
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


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
        self.rect.centery = emy.rect.centery+emy.rect.height/2
        self.speed = 6
        self.state = 'active'

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
    def __init__(self, bird: Bird, angle0=0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
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


class NeoBeam:
    """
    ビーム複数発射
    """
    def __init__(self, bird: Bird, num: int):
        self.bird = bird
        self.num = num
        
    def gen_beams(self) -> list[Beam]:
        return [Beam(self.bird, angle) for angle in range(-50, +51, int(100/(self.num-1)))]

class ReflectBeam(Beam):
    """
    一回反射したらビームが消えるクラス
    """
    def __init__(self, bird: Bird, angle0 = 0):
        super().__init__(bird, angle0)
        self.reflected = False
        self.cum = 0

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        yoko, tate = check_bound(self.rect)
        if self.cum > 100:
            if check_bound(self.rect) != (True, True):
                self.kill()
        elif self.reflected == False:
            if not yoko:
                self.vx *= -1
                self.image = pg.transform.flip(self.image, True, False)
            if not tate:
                self.vy *= -1
                self.image = pg.transform.rotozoom(self.image, 180, 1)
            self.cum += 1

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
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
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
        self.rect.centery += self.vy


class Boss(pg.sprite.Sprite):
    """
    ボスに関するクラス
    """
    imgs = [pg.transform.rotozoom(pg.image.load(f"fig/alien{i}.png"), 0, 3.0) for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = 50  # 爆弾投下インターバル
        self.hp = 5  # ボスのhp
        
    def update(self):
        """
        ボスを速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy
        if self.state == "stop" and pg.time.get_ticks() % self.interval == 0:
            return True  # 爆弾を連射する
        return False  # 爆弾を連射しない


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Gravity(pg.sprite.Sprite):
    """
    画面全体を覆う重力場を発生させるクラス
    """
    def __init__(self, life):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(255)
        self.life = life
        self.rect = self.image.get_rect()

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()           
            

class EMP(pg.sprite.Sprite):
    """
    電磁パルス
    """
    def __init__(self, enemies: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        super().__init__()
        self.enemies = enemies
        self.bombs = bombs
        self.screen = screen
        self.image = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.rect = self.image.get_rect()
        self.active = False
        self.counter = 0
    
    def activate(self):
        self.active = True
        self.counter = 3

        for enemy in self.enemies:
            enemy.interval = float('inf')
            enemy.image = pg.transform.laplacian(enemy.image)

        for bomb in self.bombs:
            bomb.speed /= 2
            bomb.state = 'inactive'

    def update(self):
        if self.active:
            self.image.fill((255, 255, 0, 128))
            self.screen.blit(self.image, self.rect)
            self.counter -= 1
            if self.counter <= 0:
                self.active = False
                self.image.fill((0, 0, 0, 0))


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    neobeams = pg.sprite.Group()
    reflectbeams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    bosses = pg.sprite.Group()
    emp = EMP(emys, bombs, screen)
    gravities = pg.sprite.Group()   # feature2

    tmr = 0
    frame = 200 #オルギル 敵の出現度を上げるためフレームを初期化
    clock = pg.time.Clock()
    boss_tmr = 0
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                if key_lst[pg.K_LSHIFT] and event.key == pg.K_SPACE and (score.value >= 100): #オルギルーこの技は最初から使えると簡単なのでスコアが何点超えると使えるようになると設定:

                    beams.add(NeoBeam(bird, 5).gen_beams())
                elif event.key == pg.K_SPACE:
                    beam = Beam(bird)
                    beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_h:
                if score.value >= 5:
                    score.value -= 5
                    beams.add(ReflectBeam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_e: 
                if score.value >= 20:
                    score.value -= 20
                    emp.activate()
            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT: #オルギル　前回追加技能をちょっと直した
                if score.value > 200: #消費スコアが200より大きい
                #K_LSHIFT から K_RSHIFTに変更
                    score.value -= 200  
                    gravities.add(Gravity(100)) #オルギル　400が長い過ぎるので100に変更
        screen.blit(bg_img, [0, 0])

        if tmr % frame == 0:  # 200フレームに1回，敵機を出現させる

            emys.add(Enemy())

        boss_tmr += clock.get_time() / 1000  # 時間の経過を秒単位
        if score.value <= 200 and boss_tmr >= 15: # scoreが200以下の時15秒ごとにボスを出現させる
            bosses.add(Boss())
            boss_tmr = 0  # ボス出現タイマーをリセット
        elif 200 <= score.value <= 500 and boss_tmr >= 7: # scoreが200から500の時7秒ごとにボスを出現させる
            bosses.add(Boss())
            boss_tmr = 0
        elif 500 <= score.value <= 900 and boss_tmr >= 3: #scoreが500から900の時3秒ごとにボスを出現させる
            bosses.add(Boss())
            boss_tmr = 0
        elif 900 <= score.value and boss_tmr >= 1: #scoreが900以上の時1秒ごとにボスを出現させる
            bosses.add(Boss())
            boss_tmr = 0

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for boss in bosses:
            if boss.update():
                bombs.add(Bomb(boss, bird))  # ボスが爆弾を連射

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for boss in pg.sprite.groupcollide(bosses, beams, False, True).keys():
            boss.hp -= 1
            if boss.hp <= 0:
                exps.add(Explosion(boss, 100))
                score.value += 100  # ボスを倒したら100点加算
                bird.change_img(6, screen)
                boss.kill()

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50)) # 爆発エフェクト

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bomb.state == "active":
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        if key_lst[pg.K_RSHIFT] and score.value > 200:  # 消費スコアが200より大きい
            score.value -= 200
            gravities.add(Gravity(100))
            

        for enemy in emys:
            for gravity in gravities:
                if pg.sprite.collide_rect(enemy, gravity):
                    exps.add(Explosion(enemy, 100))
                    enemy.kill()

        if score.value >= 1000: #スコアが1000点に達したらゲームクリア
            fonto = pg.font.Font(None, 80)
            txt = fonto.render("GameClear", True, (0, 255, 0))
            screen.blit(txt, [WIDTH/2-150, HEIGHT/2-100])
            pg.display.update()
            time.sleep(5)
            return

        gravities.update()
        gravities.draw(screen)
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        reflectbeams.update()
        reflectbeams.draw(screen)
        emys.update()
        emys.draw(screen)
        bosses.update()
        bosses.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        emp.update()
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)
        """"
        オルギル

        スコアがある時点を超えると敵の出現度が上がった行く
        """
        if score.value >= 100: #オルギル　スコアが100超えるとフレームが60になる
            frame = 60
        if score.value >= 300: #オルギル　スコアが300超えるとフレームが40になる
            frame = 40
        if score.value >= 600: #オルギル　スコアが600超えるとフレームが20になる
            frame = 20


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
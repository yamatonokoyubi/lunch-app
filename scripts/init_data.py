"""
初期データ投入スクリプト
"""

import sys
from pathlib import Path

# ルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from auth import get_password_hash
from database import SessionLocal, engine
from models import (
    Base,
    GuestCartItem,
    GuestSession,
    Menu,
    Order,
    Role,
    Store,
    User,
    UserCartItem,
    UserRole,
)


def init_database():
    """データベースとテーブルの初期化"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")


def insert_initial_data():
    """初期データの投入"""
    db = SessionLocal()

    try:
        # 既存データをクリア（外部キー制約の順序に注意）
        print("Clearing existing data...")
        db.query(Order).delete()
        db.query(Menu).delete()
        db.query(UserRole).delete()
        db.query(User).delete()
        db.query(Role).delete()
        # guest_sessions などの関連テーブルも削除
        from models import GuestSession

        db.query(GuestSession).delete()
        db.query(Store).delete()
        db.commit()
        print("✓ Existing data cleared")

        print("Inserting initial data...")

        # 1. 店舗データ（3店舗）
        print("  - Inserting stores...")
        stores = [
            Store(
                name="振徳弁当本店",
                address="宮崎県日南市飫肥4丁目2-20",
                phone_number="0987-34-5678",
                email="honten1@bento.com",
                opening_time=time(9, 0),
                closing_time=time(21, 0),
                description="毎日食べても飽きない手作り、ひとつひとつ丁寧に。まごころ込めた温かい味。ひと口食べればホッとする。こだわりの手作り弁当です。",
                image_url="https://via.placeholder.com/600x400?text=Main+Store",
                is_active=True,
            ),
            Store(
                name="振徳弁当南郷店",
                address="宮崎県日南市南郷町中村乙380-18",
                phone_number="0987-46-2111",
                email="nangou@example.com",
                opening_time=time(9, 0),
                closing_time=time(22, 0),
                description="季節の野菜を彩り豊かに使い、食べればホッとするお母さんの手作りの味を再現しました。心も体も満たされるお弁当屋さんです。",
                image_url="https://via.placeholder.com/600x400?text=Nangou+Store",
                is_active=True,
            ),
            Store(
                name="振徳弁当油津店",
                address="宮崎県日南市岩崎2丁目13",
                phone_number="0987-75-0805",
                email="aburatsu@example.com",
                opening_time=time(9, 0),
                closing_time=time(22, 0),
                description="手作りの温もりを。朝一番に仕込んだ、愛情たっぷりのお弁当です。季節の野菜を彩り豊かに使い、食べればホッとするお店です。",
                image_url="https://via.placeholder.com/600x400?text=Aburatsu+Store",
                is_active=True,
            ),
        ]
        db.add_all(stores)
        db.commit()
        print(f"    ✓ {len(stores)} stores inserted")

        # デフォルト店舗として本店を使用
        default_store = stores[0]
        db.refresh(default_store)
        print(f"    ✓ Default store: {default_store.name} (ID: {default_store.id})")

        # 2. 役割データ（店舗スタッフ用）
        print("  - Inserting roles...")
        roles_data = [
            Role(name="owner", description="店舗オーナー - 全ての権限を持つ"),
            Role(
                name="manager",
                description="店舗マネージャー - 注文管理、レポート閲覧が可能",
            ),
            Role(name="staff", description="店舗スタッフ - 注文管理のみ可能"),
        ]
        db.add_all(roles_data)
        db.commit()
        print(f"    ✓ {len(roles_data)} roles inserted")

        # roleを取得（後で使用）
        owner_role = db.query(Role).filter(Role.name == "owner").first()
        manager_role = db.query(Role).filter(Role.name == "manager").first()
        staff_role = db.query(Role).filter(Role.name == "staff").first()

        # 3. メニューデータ（30種類） - 全店舗に登録
        print("  - Inserting menus...")

        # メニューのベースデータ
        menu_templates = [
            # 1. 定番 (Classic / Standard)
            {
                "name": "彩り豊かな特製幕の内弁当",
                "price": 980,
                "description": "焼き魚、唐揚げ、煮物、だし巻き卵など、誰もが好きな定番のおかずを丁寧に詰め合わせました。お店の顔となる、まず間違いない一品です。",
                "image_url": "/static/images/menus/makunouchi_special.jpg",
            },
            {
                "name": "若鶏のジューシー唐揚げ弁当",
                "price": 780,
                "description": "特製にんにく醤油にじっくり漬け込んだ、冷めても美味しい不動の人気No.1メニュー。外はカリッと、中はジューシーな仕上がりです。",
                "image_url": "/static/images/menus/chicken_karaage.jpg",
            },
            {
                "name": "豚の生姜焼き御膳",
                "price": 850,
                "description": "ごはんが進む甘辛い特製タレで炒めた、柔らかい豚ロースの王道弁当。玉ねぎの甘みと生姜の香りが食欲をそそります。",
                "image_url": "/static/images/menus/pork_shogayaki.jpg",
            },
            {
                "name": "鶏の照り焼きと鮭塩焼きのWメイン弁当",
                "price": 920,
                "description": "肉も魚も両方食べたい、そんな欲張りな願いを叶える満足度の高い一品。甘辛い照り焼きと、脂ののった塩焼きの組み合わせが絶妙です。",
                "image_url": "/static/images/menus/w_main_terisake.jpg",
            },
            {
                "name": "定番おかずのデラックス弁当",
                "price": 1100,
                "description": "エビフライ、ミニハンバーグ、カニクリームコロッケなど、みんな大好きな洋食の人気おかずを贅沢に詰め合わせました。",
                "image_url": "/static/images/menus/deluxe_classic.jpg",
            },
            # 2. 肉の彩り (Hearty Meat)
            {
                "name": "とろけるチーズの特製ハンバーグ弁当",
                "price": 950,
                "description": "肉汁あふれるジューシーな合挽きハンバーグに、濃厚な自家製デミグラスソースと、とろけるチェダーチーズを乗せました。",
                "image_url": "/static/images/menus/cheese_hamburg.jpg",
            },
            {
                "name": "厚切り三元豚のロースかつ弁当",
                "price": 1080,
                "description": "サクサクの衣と柔らかくジューシーな肉質が自慢。厳選した三元豚を使用した、専門店の味をそのままお弁当にしました。",
                "image_url": "/static/images/menus/pork_rosukatsu.jpg",
            },
            {
                "name": "牛カルビの旨辛焼肉弁当",
                "price": 1200,
                "description": "特製の甘辛いタレで香ばしく焼き上げた、ごはんとの相性抜群の一品。食欲を刺激する香りで、スタミナ満点です。",
                "image_url": "/static/images/menus/beef_yakiniku.jpg",
            },
            {
                "name": "鶏もも肉のチキン南蛮 タルタルソース添え",
                "price": 880,
                "description": "甘酸っぱいタレを絡めたジューシーな鶏唐揚げに、卵やピクルスがたっぷり入った自家製タルタルソースを添えました。",
                "image_url": "/static/images/menus/chicken_nanban.jpg",
            },
            {
                "name": "肉好きのための3種盛り合わせ弁当（牛・豚・鶏）",
                "price": 1350,
                "description": "牛焼肉、豚の生姜焼き、鶏の照り焼きを一度に楽しめる、ボリューム満点の肉づくし弁当。心ゆくまでお肉を堪能してください。",
                "image_url": "/static/images/menus/meat_assortment.jpg",
            },
            # 3. 海の幸 (Fresh Catch)
            {
                "name": "脂ののった鯖の味噌煮弁当",
                "price": 890,
                "description": "じっくりと時間をかけて煮込み、骨まで柔らかく味が染み込んだ自慢の煮魚。こっくりとした味噌の味わいがごはんに良く合います。",
                "image_url": "/static/images/menus/saba_misoni.jpg",
            },
            {
                "name": "銀だらの西京焼き弁当",
                "price": 1280,
                "description": "上品な甘さの西京味噌に丁寧に漬け込み、ふっくらと香ばしく焼き上げた料亭の味。口の中でとろけるような食感が楽しめます。",
                "image_url": "/static/images/menus/gindara_saikyoyaki.jpg",
            },
            {
                "name": "サーモンハラスの塩麹焼き弁当",
                "price": 980,
                "description": "一番脂がのったハラスの部分を塩麹で旨味を最大限に引き出し、皮目をパリッと焼き上げました。滴る脂の旨味をご堪能ください。",
                "image_url": "/static/images/menus/salmon_harasu.jpg",
            },
            {
                "name": "海の幸フライミックス弁当（エビ・アジ・イカ）",
                "price": 1150,
                "description": "ぷりぷりのエビフライ、身がふわふわのアジフライ、柔らかいイカフライを盛り合わせました。自家製タルタルソース付きです。",
                "image_url": "/static/images/menus/seafood_fry_mix.jpg",
            },
            {
                "name": "本日入荷！旬の焼き魚御膳",
                "price": 1050,
                "description": "その日市場で仕入れた一番美味しい旬の魚を、シンプルに塩焼きで。魚本来の味をじっくりお楽しみください。※魚種は日替わりです。",
                "image_url": "/static/images/menus/seasonal_grilled_fish.jpg",
            },
            # 4. ヘルシー (Healthy)
            {
                "name": "1日に必要な野菜の半分が摂れるバランス弁当",
                "price": 920,
                "description": "緑黄色野菜を中心に、10種類以上の野菜とヘルシーな蒸し鶏を詰め合わせました。美味しく手軽に野菜不足を解消できます。",
                "image_url": "/static/images/menus/vegetable_balance.jpg",
            },
            {
                "name": "鶏むね肉のハーブ焼きと十五穀米のヘルシー弁当",
                "price": 880,
                "description": "高タンパク・低脂質な鶏むね肉をローズマリーなどのハーブで香り高く焼き上げました。ごはんは食物繊維豊富な十五穀米です。",
                "image_url": "/static/images/menus/healthy_herb_chicken.jpg",
            },
            {
                "name": "豆腐ハンバーグのきのこあんかけ弁当",
                "price": 850,
                "description": "お肉不使用でも満足感たっぷりな、ふわふわ食感の豆腐ハンバーグ。きのこの旨味が詰まった優しい味わいの和風あんかけでどうぞ。",
                "image_url": "/static/images/menus/tofu_hamburg.jpg",
            },
            {
                "name": "蒸し鶏と彩り温野菜のごま風味弁当",
                "price": 830,
                "description": "油を使わずヘルシーに調理した、しっとり柔らかい蒸し鶏と野菜の甘みが楽しめる一品。香ばしい特製ごまダレが良く合います。",
                "image_url": "/static/images/menus/steamed_chicken_veg.jpg",
            },
            {
                "name": "たっぷりグリーンサラダとグリルチキンのパワーランチ",
                "price": 950,
                "description": "ごはんの代わりに新鮮なグリーンサラダを敷き詰めた、低糖質で満足感のあるお弁当。トレーニング後のお食事にも最適です。",
                "image_url": "/static/images/menus/power_salad_lunch.jpg",
            },
            # 5. 丼もの (Donburi)
            {
                "name": "とろとろ半熟卵のロースカツ丼",
                "price": 980,
                "description": "特製の甘辛い割り下で煮込んだサクサクのロースカツを、こだわりの出汁と絶妙な半熟卵でふんわりとじました。",
                "image_url": "/static/images/menus/katsudon.jpg",
            },
            {
                "name": "大山鶏のふわとろ親子丼",
                "price": 890,
                "description": "強い旨味が特徴のブランド鶏「大山鶏」を使用し、専門店のようにつゆだくで仕上げた究極の親子丼。三つ葉の香りがアクセントです。",
                "image_url": "/static/images/menus/oyakodon.jpg",
            },
            {
                "name": "デミグラスソースのロコモコ丼 温玉のせ",
                "price": 1050,
                "description": "ジューシーなハンバーグと濃厚なデミグラスソースの組み合わせに、とろりとした温泉卵を乗せたハワイアンな丼ぶりです。",
                "image_url": "/static/images/menus/locomoco_don.jpg",
            },
            {
                "name": "特製たれの海鮮づけ丼",
                "price": 1380,
                "description": "マグロやサーモン、イカなど数種類の新鮮な魚介を、風味豊かな特製の醤油だれに漬け込んだ贅沢な丼。薬味と一緒にお楽しみください。",
                "image_url": "/static/images/menus/kaisen_don.jpg",
            },
            {
                "name": "揚げたて大海老と野菜の天丼",
                "price": 1180,
                "description": "食べ応えのある大きな海老天2本と、なすやカボチャなど季節野菜の天ぷらを盛り付けました。秘伝の甘辛い丼タレが味の決め手です。",
                "image_url": "/static/images/menus/tendon.jpg",
            },
            # 6. サイドメニュー (Side Dishes)
            {
                "name": "10種野菜のグリーンサラダ（選べるドレッシング）",
                "price": 250,
                "description": "お弁当にもう一品。レタスやトマト、パプリカなど、新鮮な野菜をたっぷり摂れるミニサラダです。（和風／シーザー）",
                "image_url": "/static/images/menus/green_salad.jpg",
            },
            {
                "name": "あおさと豆腐の合わせ味噌汁",
                "price": 180,
                "description": "磯の香りが豊かなあおさと、なめらかな絹ごし豆腐が入った、心も体も温まる一杯。お弁当とご一緒にどうぞ。",
                "image_url": "/static/images/menus/miso_soup.jpg",
            },
            {
                "name": "ちょい足し唐揚げ（3個）",
                "price": 280,
                "description": "もう少し食べたい時にぴったりな、当店自慢のジューシーな唐揚げです。お弁当のおかずにプラスして満足度アップ。",
                "image_url": "/static/images/menus/side_karaage.jpg",
            },
            {
                "name": "ほうれん草のごま和え",
                "price": 150,
                "description": "お弁当の彩りと栄養バランスをプラスする、定番の和惣菜。香ばしいごまの風味が食欲をそそります。",
                "image_url": "/static/images/menus/horenso_gomaae.jpg",
            },
            {
                "name": "なめらか絹プリン",
                "price": 320,
                "description": "食後のデザートに。新鮮な卵と牛乳、生クリームを贅沢に使った、とろける口当たりの自家製プリンです。ほろ苦いカラメルがアクセント。",
                "image_url": "/static/images/menus/pudding.jpg",
            },
        ]

        # 各店舗にメニューを登録
        menus = []
        for store in stores:
            for template in menu_templates:
                menu = Menu(
                    name=template["name"],
                    price=template["price"],
                    description=template["description"],
                    image_url=template["image_url"],
                    store_id=store.id,
                )
                menus.append(menu)

        db.add_all(menus)
        db.commit()
        print(f"    ✓ {len(menus)} menus inserted (30 menus × {len(stores)} stores)")

        # 4. ユーザーデータ
        print("  - Inserting store staff...")
        store_users = [
            User(
                username="admin",
                email="admin@bento.com",
                hashed_password=get_password_hash("admin@123"),
                role="store",
                full_name="管理者",
                store_id=default_store.id,
            ),
            User(
                username="store1",
                email="store1@bento.com",
                hashed_password=get_password_hash("password123"),
                role="store",
                full_name="佐藤花子",
                store_id=default_store.id,
            ),
            User(
                username="store2",
                email="store2@bento.com",
                hashed_password=get_password_hash("password123"),
                role="store",
                full_name="鈴木一郎",
                store_id=default_store.id,
            ),
        ]
        db.add_all(store_users)
        db.commit()
        print(f"    ✓ {len(store_users)} store staff inserted")

        # 店舗ユーザーに役割を割り当て
        print("  - Assigning roles to store staff...")
        admin_user = db.query(User).filter(User.username == "admin").first()
        store1_user = db.query(User).filter(User.username == "store1").first()
        store2_user = db.query(User).filter(User.username == "store2").first()

        user_roles = [
            UserRole(user_id=admin_user.id, role_id=owner_role.id),  # admin = owner
            UserRole(
                user_id=store1_user.id, role_id=manager_role.id
            ),  # store1 = manager
            UserRole(user_id=store2_user.id, role_id=staff_role.id),  # store2 = staff
        ]
        db.add_all(user_roles)
        db.commit()
        print(f"    ✓ {len(user_roles)} role assignments created")

        print("  - Inserting customers...")
        customers = [
            User(
                username="customer1",
                email="customer1@example.com",
                hashed_password=get_password_hash("password123"),
                role="customer",
                full_name="山田太郎",
            ),
            User(
                username="customer2",
                email="customer2@example.com",
                hashed_password=get_password_hash("password123"),
                role="customer",
                full_name="田中美咲",
            ),
            User(
                username="customer3",
                email="customer3@example.com",
                hashed_password=get_password_hash("password123"),
                role="customer",
                full_name="伊藤健太",
            ),
            User(
                username="customer4",
                email="customer4@example.com",
                hashed_password=get_password_hash("password123"),
                role="customer",
                full_name="高橋さくら",
            ),
            User(
                username="customer5",
                email="customer5@example.com",
                hashed_password=get_password_hash("password123"),
                role="customer",
                full_name="渡辺健二",
            ),
        ]
        db.add_all(customers)
        db.commit()
        print(f"    ✓ {len(customers)} customers inserted")

        # 5. 販売データ
        print("  - Inserting orders...")
        customer_users = db.query(User).filter(User.role == "customer").all()
        menu_items = db.query(Menu).all()

        orders_data = [
            {
                "user": customer_users[0],
                "menu": menu_items[0],
                "quantity": 2,
                "status": "completed",
                "days_ago": 7,
                "hour": 10,
                "time": "12:00:00",
                "notes": "なし",
            },
            {
                "user": customer_users[1],
                "menu": menu_items[2],
                "quantity": 1,
                "status": "completed",
                "days_ago": 7,
                "hour": 11,
                "time": "12:30:00",
                "notes": "お箸不要",
            },
            {
                "user": customer_users[2],
                "menu": menu_items[1],
                "quantity": 1,
                "status": "completed",
                "days_ago": 7,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[0],
                "menu": menu_items[4],
                "quantity": 1,
                "status": "completed",
                "days_ago": 6,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[3],
                "menu": menu_items[3],
                "quantity": 2,
                "status": "completed",
                "days_ago": 6,
                "hour": 9,
                "time": "11:30:00",
                "notes": "温めてください",
            },
            {
                "user": customer_users[4],
                "menu": menu_items[0],
                "quantity": 3,
                "status": "completed",
                "days_ago": 6,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[1],
                "menu": menu_items[5],
                "quantity": 1,
                "status": "completed",
                "days_ago": 5,
                "hour": 11,
                "time": "13:00:00",
                "notes": "醤油多めで",
            },
            {
                "user": customer_users[2],
                "menu": menu_items[0],
                "quantity": 2,
                "status": "completed",
                "days_ago": 5,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[0],
                "menu": menu_items[1],
                "quantity": 1,
                "status": "completed",
                "days_ago": 4,
                "hour": 10,
                "time": "12:30:00",
                "notes": None,
            },
            {
                "user": customer_users[3],
                "menu": menu_items[2],
                "quantity": 2,
                "status": "completed",
                "days_ago": 4,
                "hour": 10,
                "time": "12:00:00",
                "notes": "2つ別々に包装",
            },
            {
                "user": customer_users[4],
                "menu": menu_items[4],
                "quantity": 1,
                "status": "completed",
                "days_ago": 4,
                "hour": 9,
                "time": "11:30:00",
                "notes": None,
            },
            {
                "user": customer_users[1],
                "menu": menu_items[0],
                "quantity": 1,
                "status": "completed",
                "days_ago": 3,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[2],
                "menu": menu_items[3],
                "quantity": 1,
                "status": "completed",
                "days_ago": 3,
                "hour": 10,
                "time": "12:30:00",
                "notes": None,
            },
            {
                "user": customer_users[0],
                "menu": menu_items[5],
                "quantity": 1,
                "status": "completed",
                "days_ago": 3,
                "hour": 11,
                "time": "13:00:00",
                "notes": "わさび抜き",
            },
            {
                "user": customer_users[3],
                "menu": menu_items[1],
                "quantity": 2,
                "status": "completed",
                "days_ago": 2,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[4],
                "menu": menu_items[2],
                "quantity": 1,
                "status": "completed",
                "days_ago": 2,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[0],
                "menu": menu_items[0],
                "quantity": 2,
                "status": "completed",
                "days_ago": 1,
                "hour": 10,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[1],
                "menu": menu_items[4],
                "quantity": 1,
                "status": "ready",
                "days_ago": 1,
                "hour": 10,
                "time": "12:30:00",
                "notes": None,
            },
            {
                "user": customer_users[2],
                "menu": menu_items[1],
                "quantity": 1,
                "status": "preparing",
                "days_ago": 0,
                "hour": -2,
                "time": "12:00:00",
                "notes": None,
            },
            {
                "user": customer_users[3],
                "menu": menu_items[3],
                "quantity": 1,
                "status": "confirmed",
                "days_ago": 0,
                "hour": -1,
                "time": "13:00:00",
                "notes": "レモン多めで",
            },
        ]

        orders = []
        for order_data in orders_data:
            if order_data["days_ago"] == 0:
                ordered_at = datetime.now() + timedelta(hours=order_data["hour"])
            else:
                ordered_at = (
                    datetime.now()
                    - timedelta(days=order_data["days_ago"])
                    + timedelta(hours=order_data["hour"])
                )
            total_price = order_data["menu"].price * order_data["quantity"]
            delivery_time_obj = None
            if order_data["time"]:
                hour, minute, second = map(int, order_data["time"].split(":"))
                delivery_time_obj = time(hour, minute, second)

            order = Order(
                user_id=order_data["user"].id,
                menu_id=order_data["menu"].id,
                store_id=default_store.id,
                quantity=order_data["quantity"],
                total_price=total_price,
                status=order_data["status"],
                delivery_time=delivery_time_obj,
                notes=order_data["notes"],
                ordered_at=ordered_at,
            )
            orders.append(order)

        db.add_all(orders)
        db.commit()
        print(f"    ✓ {len(orders)} orders inserted")

        print("\n✓ All initial data inserted successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error inserting initial data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
    insert_initial_data()
    print("\nDatabase initialization completed!")

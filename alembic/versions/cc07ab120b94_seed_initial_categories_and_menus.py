"""seed initial categories and menus

Revision ID: cc07ab120b94
Revises: 003_simplify_status
Create Date: 2025-10-17 12:47:45.922355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'cc07ab120b94'
down_revision: Union[str, None] = '004_menu_categories'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """初期カテゴリとメニューデータを投入"""
    conn = op.get_bind()
    
    # 既に実行済みかチェック（冪等性の確保）
    result = conn.execute(text("SELECT COUNT(*) FROM menu_categories WHERE name IN ('定番', '肉の彩り', '海の幸', 'ヘルシー', '丼もの', 'サイドメニュー')"))
    existing_count = result.fetchone()[0]
    if existing_count >= 6:
        print("✓ 初期データは既に投入されています。スキップします。")
        return
    
    # デフォルト店舗を取得または作成
    result = conn.execute(text("SELECT id FROM stores ORDER BY id LIMIT 1"))
    store_row = result.fetchone()
    
    if not store_row:
        print("デフォルト店舗が見つかりません。新規作成します...")
        conn.execute(
            text("""
                INSERT INTO stores (name, address, phone_number, email, opening_time, closing_time, description, image_url, is_active, created_at, updated_at)
                VALUES (:name, :address, :phone, :email, :opening, :closing, :desc, :image, :active, NOW(), NOW())
            """),
            {
                'name': '新徳弁当飫肥店',
                'address': '東京都渋谷区1-2-3',
                'phone': '03-1234-5678',
                'email': 'obi@bento.com',
                'opening': '09:00:00',
                'closing': '20:00:00',
                'desc': '美味しい弁当をお届けする本店です。',
                'image': 'https://via.placeholder.com/600x400?text=Main+Store',
                'active': True
            }
        )
        result = conn.execute(text("SELECT id FROM stores ORDER BY id LIMIT 1"))
        store_row = result.fetchone()
        print(f"✓ デフォルト店舗を作成しました（ID: {store_row[0]}）")
    
    default_store_id = store_row[0]
    
    # 1. カテゴリデータを投入
    categories = [
        {'name': '定番', 'description': '幕の内や唐揚げなど、誰もが好きな定番の味', 'display_order': 1, 'is_active': True, 'store_id': default_store_id},
        {'name': '肉の彩り', 'description': 'ハンバーグやカツなど、お肉をたっぷり楽しむボリューム満点メニュー', 'display_order': 2, 'is_active': True, 'store_id': default_store_id},
        {'name': '海の幸', 'description': '新鮮な魚介を使った、魚好きにはたまらないラインナップ', 'display_order': 3, 'is_active': True, 'store_id': default_store_id},
        {'name': 'ヘルシー', 'description': '野菜たっぷり、低カロリーで健康を気遣う方におすすめ', 'display_order': 4, 'is_active': True, 'store_id': default_store_id},
        {'name': '丼もの', 'description': 'ボリューム満点、がっつり食べたい時の丼ぶりメニュー', 'display_order': 5, 'is_active': True, 'store_id': default_store_id},
        {'name': 'サイドメニュー', 'description': 'お弁当にプラスして、より豊かな食事を', 'display_order': 6, 'is_active': True, 'store_id': default_store_id},
    ]
    
    for category in categories:
        conn.execute(
            text("""
                INSERT INTO menu_categories (name, description, display_order, is_active, store_id, created_at, updated_at)
                VALUES (:name, :description, :display_order, :is_active, :store_id, NOW(), NOW())
            """),
            category
        )
    
    # カテゴリIDを取得
    category_ids = {}
    for cat_name in ['定番', '肉の彩り', '海の幸', 'ヘルシー', '丼もの', 'サイドメニュー']:
        result = conn.execute(
            text("SELECT id FROM menu_categories WHERE name = :name AND store_id = :store_id"),
            {'name': cat_name, 'store_id': default_store_id}
        )
        row = result.fetchone()
        if row:
            category_ids[cat_name] = row[0]
    
    # 2. メニューデータを投入
    menus = [
        # 定番 (5品)
        {'name': '彩り豊かな特製幕の内弁当', 'price': 980, 'description': '焼き魚、唐揚げ、煮物、だし巻き卵など、誰もが好きな定番のおかずを丁寧に詰め合わせました。お店の顔となる、まず間違いない一品です。', 'image_url': '/static/images/menus/makunouchi_special.jpg', 'category_id': category_ids.get('定番')},
        {'name': '若鶏のジューシー唐揚げ弁当', 'price': 780, 'description': '特製にんにく醤油にじっくり漬け込んだ、冷めても美味しい不動の人気No.1メニュー。外はカリッと、中はジューシーな仕上がりです。', 'image_url': '/static/images/menus/chicken_karaage.jpg', 'category_id': category_ids.get('定番')},
        {'name': '豚の生姜焼き御膳', 'price': 850, 'description': 'ごはんが進む甘辛い特製タレで炒めた、柔らかい豚ロースの王道弁当。玉ねぎの甘みと生姜の香りが食欲をそそります。', 'image_url': '/static/images/menus/pork_shogayaki.jpg', 'category_id': category_ids.get('定番')},
        {'name': '鶏の照り焼きと鮭塩焼きのWメイン弁当', 'price': 920, 'description': '肉も魚も両方食べたい、そんな欲張りな願いを叶える満足度の高い一品。甘辛い照り焼きと、脂ののった塩焼きの組み合わせが絶妙です。', 'image_url': '/static/images/menus/w_main_terisake.jpg', 'category_id': category_ids.get('定番')},
        {'name': '定番おかずのデラックス弁当', 'price': 1100, 'description': 'エビフライ、ミニハンバーグ、カニクリームコロッケなど、みんな大好きな洋食の人気おかずを贅沢に詰め合わせました。', 'image_url': '/static/images/menus/deluxe_classic.jpg', 'category_id': category_ids.get('定番')},
        
        # 肉の彩り (5品)
        {'name': 'とろけるチーズの特製ハンバーグ弁当', 'price': 950, 'description': '肉汁あふれるジューシーな合挽きハンバーグに、濃厚な自家製デミグラスソースと、とろけるチェダーチーズを乗せました。', 'image_url': '/static/images/menus/cheese_hamburg.jpg', 'category_id': category_ids.get('肉の彩り')},
        {'name': '厚切り三元豚のロースかつ弁当', 'price': 1080, 'description': 'サクサクの衣と柔らかくジューシーな肉質が自慢。厳選した三元豚を使用した、専門店の味をそのままお弁当にしました。', 'image_url': '/static/images/menus/pork_rosukatsu.jpg', 'category_id': category_ids.get('肉の彩り')},
        {'name': '牛カルビの旨辛焼肉弁当', 'price': 1200, 'description': '特製の甘辛いタレで香ばしく焼き上げた、ごはんとの相性抜群の一品。食欲を刺激する香りで、スタミナ満点です。', 'image_url': '/static/images/menus/beef_yakiniku.jpg', 'category_id': category_ids.get('肉の彩り')},
        {'name': '鶏もも肉のチキン南蛮 タルタルソース添え', 'price': 880, 'description': '甘酸っぱいタレを絡めたジューシーな鶏唐揚げに、卵やピクルスがたっぷり入った自家製タルタルソースを添えました。', 'image_url': '/static/images/menus/chicken_nanban.jpg', 'category_id': category_ids.get('肉の彩り')},
        {'name': '肉好きのための3種盛り合わせ弁当（牛・豚・鶏）', 'price': 1350, 'description': '牛焼肉、豚の生姜焼き、鶏の照り焼きを一度に楽しめる、ボリューム満点の肉づくし弁当。心ゆくまでお肉を堪能してください。', 'image_url': '/static/images/menus/meat_assortment.jpg', 'category_id': category_ids.get('肉の彩り')},
        
        # 海の幸 (5品)
        {'name': '脂ののった鯖の味噌煮弁当', 'price': 890, 'description': 'じっくりと時間をかけて煮込み、骨まで柔らかく味が染み込んだ自慢の煮魚。こっくりとした味噌の味わいがごはんに良く合います。', 'image_url': '/static/images/menus/saba_misoni.jpg', 'category_id': category_ids.get('海の幸')},
        {'name': '銀だらの西京焼き弁当', 'price': 1280, 'description': '上品な甘さの西京味噌に丁寧に漬け込み、ふっくらと香ばしく焼き上げた料亭の味。口の中でとろけるような食感が楽しめます。', 'image_url': '/static/images/menus/gindara_saikyoyaki.jpg', 'category_id': category_ids.get('海の幸')},
        {'name': 'サーモンハラスの塩麹焼き弁当', 'price': 980, 'description': '一番脂がのったハラスの部分を塩麹で旨味を最大限に引き出し、皮目をパリッと焼き上げました。滴る脂の旨味をご堪能ください。', 'image_url': '/static/images/menus/salmon_harasu.jpg', 'category_id': category_ids.get('海の幸')},
        {'name': '海の幸フライミックス弁当（エビ・アジ・イカ）', 'price': 1150, 'description': 'ぷりぷりのエビフライ、身がふわふわのアジフライ、柔らかいイカフライを盛り合わせました。自家製タルタルソース付きです。', 'image_url': '/static/images/menus/seafood_fry_mix.jpg', 'category_id': category_ids.get('海の幸')},
        {'name': '本日入荷！旬の焼き魚御膳', 'price': 1050, 'description': 'その日市場で仕入れた一番美味しい旬の魚を、シンプルに塩焼きで。魚本来の味をじっくりお楽しみください。※魚種は日替わりです。', 'image_url': '/static/images/menus/seasonal_grilled_fish.jpg', 'category_id': category_ids.get('海の幸')},
        
        # ヘルシー (5品)
        {'name': '1日に必要な野菜の半分が摂れるバランス弁当', 'price': 920, 'description': '緑黄色野菜を中心に、10種類以上の野菜とヘルシーな蒸し鶏を詰め合わせました。美味しく手軽に野菜不足を解消できます。', 'image_url': '/static/images/menus/vegetable_balance.jpg', 'category_id': category_ids.get('ヘルシー')},
        {'name': '鶏むね肉のハーブ焼きと十五穀米のヘルシー弁当', 'price': 880, 'description': '高タンパク・低脂質な鶏むね肉をローズマリーなどのハーブで香り高く焼き上げました。ごはんは食物繊維豊富な十五穀米です。', 'image_url': '/static/images/menus/healthy_herb_chicken.jpg', 'category_id': category_ids.get('ヘルシー')},
        {'name': '豆腐ハンバーグのきのこあんかけ弁当', 'price': 850, 'description': 'お肉不使用でも満足感たっぷりな、ふわふわ食感の豆腐ハンバーグ。きのこの旨味が詰まった優しい味わいの和風あんかけでどうぞ。', 'image_url': '/static/images/menus/tofu_hamburg.jpg', 'category_id': category_ids.get('ヘルシー')},
        {'name': '蒸し鶏と彩り温野菜のごま風味弁当', 'price': 830, 'description': '油を使わずヘルシーに調理した、しっとり柔らかい蒸し鶏と野菜の甘みが楽しめる一品。香ばしい特製ごまダレが良く合います。', 'image_url': '/static/images/menus/steamed_chicken_veg.jpg', 'category_id': category_ids.get('ヘルシー')},
        {'name': 'たっぷりグリーンサラダとグリルチキンのパワーランチ', 'price': 950, 'description': 'ごはんの代わりに新鮮なグリーンサラダを敷き詰めた、低糖質で満足感のあるお弁当。トレーニング後のお食事にも最適です。', 'image_url': '/static/images/menus/power_salad_lunch.jpg', 'category_id': category_ids.get('ヘルシー')},
        
        # 丼もの (5品)
        {'name': 'とろとろ半熟卵のロースカツ丼', 'price': 980, 'description': '特製の甘辛い割り下で煮込んだサクサクのロースカツを、こだわりの出汁と絶妙な半熟卵でふんわりとじました。', 'image_url': '/static/images/menus/katsudon.jpg', 'category_id': category_ids.get('丼もの')},
        {'name': '大山鶏のふわとろ親子丼', 'price': 890, 'description': '強い旨味が特徴のブランド鶏「大山鶏」を使用し、専門店のようにつゆだくで仕上げた究極の親子丼。三つ葉の香りがアクセントです。', 'image_url': '/static/images/menus/oyakodon.jpg', 'category_id': category_ids.get('丼もの')},
        {'name': 'デミグラスソースのロコモコ丼 温玉のせ', 'price': 1050, 'description': 'ジューシーなハンバーグと濃厚なデミグラスソースの組み合わせに、とろりとした温泉卵を乗せたハワイアンな丼ぶりです。', 'image_url': '/static/images/menus/locomoco_don.jpg', 'category_id': category_ids.get('丼もの')},
        {'name': '特製たれの海鮮づけ丼', 'price': 1380, 'description': 'マグロやサーモン、イカなど数種類の新鮮な魚介を、風味豊かな特製の醤油だれに漬け込んだ贅沢な丼。薬味と一緒にお楽しみください。', 'image_url': '/static/images/menus/kaisen_don.jpg', 'category_id': category_ids.get('丼もの')},
        {'name': '揚げたて大海老と野菜の天丼', 'price': 1180, 'description': '食べ応えのある大きな海老天2本と、なすやカボチャなど季節野菜の天ぷらを盛り付けました。秘伝の甘辛い丼タレが味の決め手です。', 'image_url': '/static/images/menus/tendon.jpg', 'category_id': category_ids.get('丼もの')},
        
        # サイドメニュー (5品)
        {'name': '10種野菜のグリーンサラダ（選べるドレッシング）', 'price': 250, 'description': 'お弁当にもう一品。レタスやトマト、パプリカなど、新鮮な野菜をたっぷり摂れるミニサラダです。（和風／シーザー）', 'image_url': '/static/images/menus/green_salad.jpg', 'category_id': category_ids.get('サイドメニュー')},
        {'name': 'あおさと豆腐の合わせ味噌汁', 'price': 180, 'description': '磯の香りが豊かなあおさと、なめらかな絹ごし豆腐が入った、心も体も温まる一杯。お弁当とご一緒にどうぞ。', 'image_url': '/static/images/menus/miso_soup.jpg', 'category_id': category_ids.get('サイドメニュー')},
        {'name': 'ちょい足し唐揚げ（3個）', 'price': 280, 'description': 'もう少し食べたい時にぴったりな、当店自慢のジューシーな唐揚げです。お弁当のおかずにプラスして満足度アップ。', 'image_url': '/static/images/menus/side_karaage.jpg', 'category_id': category_ids.get('サイドメニュー')},
        {'name': 'ほうれん草のごま和え', 'price': 150, 'description': 'お弁当の彩りと栄養バランスをプラスする、定番の和惣菜。香ばしいごまの風味が食欲をそそります。', 'image_url': '/static/images/menus/horenso_gomaae.jpg', 'category_id': category_ids.get('サイドメニュー')},
        {'name': 'なめらか絹プリン', 'price': 320, 'description': '食後のデザートに。新鮮な卵と牛乳、生クリームを贅沢に使った、とろける口当たりの自家製プリンです。ほろ苦いカラメルがアクセント。', 'image_url': '/static/images/menus/pudding.jpg', 'category_id': category_ids.get('サイドメニュー')},
    ]
    
    for menu in menus:
        conn.execute(
            text("""
                INSERT INTO menus (name, price, description, image_url, is_available, category_id, store_id, created_at, updated_at)
                VALUES (:name, :price, :description, :image_url, TRUE, :category_id, :store_id, NOW(), NOW())
            """),
            {**menu, 'store_id': default_store_id}
        )
    
    print(f"✓ 6カテゴリと30種類のメニューを投入しました（店舗ID: {default_store_id}）")
    
    # 3. 役割データを投入
    roles_data = [
        {'name': 'owner', 'description': '店舗オーナー - 全ての権限を持つ'},
        {'name': 'manager', 'description': '店舗マネージャー - 注文管理、レポート閲覧が可能'},
        {'name': 'staff', 'description': '店舗スタッフ - 注文管理のみ可能'}
    ]
    
    for role in roles_data:
        conn.execute(
            text("""
                INSERT INTO roles (name, description, created_at)
                VALUES (:name, :description, NOW())
                ON CONFLICT (name) DO NOTHING
            """),
            role
        )
    
    # 役割IDを取得
    role_ids = {}
    for role_name in ['owner', 'manager', 'staff']:
        result = conn.execute(
            text("SELECT id FROM roles WHERE name = :name"),
            {'name': role_name}
        )
        row = result.fetchone()
        if row:
            role_ids[role_name] = row[0]
    
    # 4. ユーザーデータを投入（パスワードハッシュは事前に生成）
    # 既存ユーザーをチェック
    result = conn.execute(text("SELECT COUNT(*) FROM users WHERE username IN ('admin', 'store1', 'store2', 'customer1', 'customer2', 'customer3', 'customer4', 'customer5')"))
    existing_users = result.fetchone()[0]
    if existing_users > 0:
        print(f"✓ {existing_users}名のデモユーザーが既に存在します。ユーザー作成をスキップします。")
    else:
        # パスワード: admin@123 と password123 のbcryptハッシュ
        import bcrypt
        admin_password = bcrypt.hashpw("admin@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_password = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
        # 店舗スタッフ
        store_users = [
            {'username': 'admin', 'email': 'admin@bento.com', 'password': admin_password, 'role': 'store', 'full_name': '管理者', 'store_id': default_store_id, 'is_active': True},
            {'username': 'store1', 'email': 'store1@bento.com', 'password': user_password, 'role': 'store', 'full_name': '佐藤花子', 'store_id': default_store_id, 'is_active': True},
            {'username': 'store2', 'email': 'store2@bento.com', 'password': user_password, 'role': 'store', 'full_name': '鈴木一郎', 'store_id': default_store_id, 'is_active': True}
        ]
        
        for user in store_users:
            conn.execute(
                text("""
                    INSERT INTO users (username, email, hashed_password, role, full_name, store_id, is_active, created_at)
                    VALUES (:username, :email, :password, :role, :full_name, :store_id, :is_active, NOW())
                """),
                user
            )
        
        # ユーザーIDを取得して役割を割り当て
        result = conn.execute(text("SELECT id FROM users WHERE username = 'admin'"))
        admin_id = result.fetchone()[0]
        result = conn.execute(text("SELECT id FROM users WHERE username = 'store1'"))
        store1_id = result.fetchone()[0]
        result = conn.execute(text("SELECT id FROM users WHERE username = 'store2'"))
        store2_id = result.fetchone()[0]
        
        user_role_assignments = [
            {'user_id': admin_id, 'role_id': role_ids['owner']},
            {'user_id': store1_id, 'role_id': role_ids['manager']},
            {'user_id': store2_id, 'role_id': role_ids['staff']}
        ]
        
        for assignment in user_role_assignments:
            conn.execute(
                text("""
                    INSERT INTO user_roles (user_id, role_id, assigned_at)
                    VALUES (:user_id, :role_id, NOW())
                """),
                assignment
            )
        
        # 顧客ユーザー
        customers = [
            {'username': 'customer1', 'email': 'customer1@example.com', 'password': user_password, 'role': 'customer', 'full_name': '山田太郎', 'is_active': True},
            {'username': 'customer2', 'email': 'customer2@example.com', 'password': user_password, 'role': 'customer', 'full_name': '田中美咲', 'is_active': True},
            {'username': 'customer3', 'email': 'customer3@example.com', 'password': user_password, 'role': 'customer', 'full_name': '伊藤健太', 'is_active': True},
            {'username': 'customer4', 'email': 'customer4@example.com', 'password': user_password, 'role': 'customer', 'full_name': '高橋さくら', 'is_active': True},
            {'username': 'customer5', 'email': 'customer5@example.com', 'password': user_password, 'role': 'customer', 'full_name': '渡辺健二', 'is_active': True}
        ]
        
        for customer in customers:
            conn.execute(
                text("""
                    INSERT INTO users (username, email, hashed_password, role, full_name, is_active, created_at)
                    VALUES (:username, :email, :password, :role, :full_name, :is_active, NOW())
                """),
                customer
            )
        
        print(f"✓ 8ユーザー（店舗スタッフ3名、顧客5名）を投入しました")


def downgrade() -> None:
    """投入したカテゴリとメニューデータを削除"""
    conn = op.get_bind()
    
    # このマイグレーションで追加したメニューを削除
    menu_names = [
        '彩り豊かな特製幕の内弁当', '若鶏のジューシー唐揚げ弁当', '豚の生姜焼き御膳', '鶏の照り焼きと鮭塩焼きのWメイン弁当', '定番おかずのデラックス弁当',
        'とろけるチーズの特製ハンバーグ弁当', '厚切り三元豚のロースかつ弁当', '牛カルビの旨辛焼肉弁当', '鶏もも肉のチキン南蛮 タルタルソース添え', '肉好きのための3種盛り合わせ弁当（牛・豚・鶏）',
        '脂ののった鯖の味噌煮弁当', '銀だらの西京焼き弁当', 'サーモンハラスの塩麹焼き弁当', '海の幸フライミックス弁当（エビ・アジ・イカ）', '本日入荷！旬の焼き魚御膳',
        '1日に必要な野菜の半分が摂れるバランス弁当', '鶏むね肉のハーブ焼きと十五穀米のヘルシー弁当', '豆腐ハンバーグのきのこあんかけ弁当', '蒸し鶏と彩り温野菜のごま風味弁当', 'たっぷりグリーンサラダとグリルチキンのパワーランチ',
        'とろとろ半熟卵のロースカツ丼', '大山鶏のふわとろ親子丼', 'デミグラスソースのロコモコ丼 温玉のせ', '特製たれの海鮮づけ丼', '揚げたて大海老と野菜の天丼',
        '10種野菜のグリーンサラダ（選べるドレッシング）', 'あおさと豆腐の合わせ味噌汁', 'ちょい足し唐揚げ（3個）', 'ほうれん草のごま和え', 'なめらか絹プリン'
    ]
    
    for name in menu_names:
        conn.execute(
            text("DELETE FROM menus WHERE name = :name"),
            {'name': name}
        )
    
    # このマイグレーションで追加したカテゴリを削除
    category_names = ['定番', '肉の彩り', '海の幸', 'ヘルシー', '丼もの', 'サイドメニュー']
    for name in category_names:
        conn.execute(
            text("DELETE FROM menu_categories WHERE name = :name"),
            {'name': name}
        )
    
    # このマイグレーションで追加したユーザーを削除
    user_names = ['admin', 'store1', 'store2', 'customer1', 'customer2', 'customer3', 'customer4', 'customer5']
    for username in user_names:
        conn.execute(
            text("DELETE FROM users WHERE username = :username"),
            {'username': username}
        )
    
    # このマイグレーションで追加した役割を削除
    role_names = ['owner', 'manager', 'staff']
    for role_name in role_names:
        conn.execute(
            text("DELETE FROM roles WHERE name = :role_name"),
            {'role_name': role_name}
        )
    
    # このマイグレーションで追加した店舗を削除（名前で識別）
    conn.execute(
        text("DELETE FROM stores WHERE name = :name"),
        {'name': '新徳弁当飫肥店'}
    )
    
    print("✓ 投入したカテゴリ、メニュー、ユーザー、役割、店舗を削除しました")

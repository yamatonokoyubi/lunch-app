"""
メニュー画像アップロード機能のテスト
"""

import pytest
import io
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from main import app
from tests.conftest import client, test_db, test_user_store1, auth_headers_store1


def create_test_image(format='JPEG', size=(100, 100), color=(255, 0, 0)):
    """テスト用の画像ファイルを作成"""
    img = Image.new('RGB', size, color)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=format)
    img_byte_arr.seek(0)
    return img_byte_arr


class TestMenuImageUpload:
    """メニュー画像アップロードのテスト"""

    def test_upload_menu_image_success_jpeg(self, client, test_db, auth_headers_store1):
        """正常系: JPEG画像のアップロード"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "description": "テスト用の弁当です",
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        assert response.status_code == 200
        menu_id = response.json()["id"]

        # JPEG画像をアップロード
        image_file = create_test_image(format='JPEG')
        files = {"file": ("test_image.jpg", image_file, "image/jpeg")}
        
        response = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files,
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] is not None
        assert "/static/images/menus/" in data["image_url"]
        assert data["image_url"].endswith(".jpg") or data["image_url"].endswith(".jpeg")

        # ファイルが実際に保存されているか確認
        image_path = Path(data["image_url"].lstrip('/'))
        assert image_path.exists()
        
        # クリーンアップ
        if image_path.exists():
            image_path.unlink()

    def test_upload_menu_image_success_png(self, client, test_db, auth_headers_store1):
        """正常系: PNG画像のアップロード"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        menu_id = response.json()["id"]

        # PNG画像をアップロード
        image_file = create_test_image(format='PNG')
        files = {"file": ("test_image.png", image_file, "image/png")}
        
        response = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files,
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_url"].endswith(".png")

        # クリーンアップ
        image_path = Path(data["image_url"].lstrip('/'))
        if image_path.exists():
            image_path.unlink()

    def test_upload_menu_image_replace_old_image(self, client, test_db, auth_headers_store1):
        """正常系: 古い画像を新しい画像で置き換え"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        menu_id = response.json()["id"]

        # 最初の画像をアップロード
        image_file1 = create_test_image(format='JPEG', color=(255, 0, 0))
        files1 = {"file": ("image1.jpg", image_file1, "image/jpeg")}
        response1 = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files1,
            headers=auth_headers_store1
        )
        assert response1.status_code == 200
        old_image_url = response1.json()["image_url"]
        old_image_path = Path(old_image_url.lstrip('/'))
        assert old_image_path.exists()

        # 2番目の画像をアップロード（置き換え）
        image_file2 = create_test_image(format='PNG', color=(0, 255, 0))
        files2 = {"file": ("image2.png", image_file2, "image/png")}
        response2 = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files2,
            headers=auth_headers_store1
        )
        assert response2.status_code == 200
        new_image_url = response2.json()["image_url"]
        new_image_path = Path(new_image_url.lstrip('/'))

        # 古い画像が削除されていることを確認
        assert not old_image_path.exists()
        # 新しい画像が存在することを確認
        assert new_image_path.exists()

        # クリーンアップ
        if new_image_path.exists():
            new_image_path.unlink()

    def test_upload_menu_image_invalid_format(self, client, test_db, auth_headers_store1):
        """異常系: 無効なファイル形式（テキストファイル）"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        menu_id = response.json()["id"]

        # テキストファイルをアップロード
        text_file = io.BytesIO(b"This is a text file")
        files = {"file": ("test.txt", text_file, "text/plain")}
        
        response = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files,
            headers=auth_headers_store1
        )
        
        assert response.status_code == 400
        assert "Invalid file format" in response.json()["detail"]

    def test_upload_menu_image_file_too_large(self, client, test_db, auth_headers_store1):
        """異常系: ファイルサイズ超過（2MB以上）"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        menu_id = response.json()["id"]

        # 大きな画像を作成（2MB超）
        large_image = create_test_image(format='JPEG', size=(3000, 3000))
        files = {"file": ("large_image.jpg", large_image, "image/jpeg")}
        
        response = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files,
            headers=auth_headers_store1
        )
        
        assert response.status_code == 400
        assert "exceeds maximum allowed size" in response.json()["detail"]

    def test_upload_menu_image_menu_not_found(self, client, test_db, auth_headers_store1):
        """異常系: 存在しないメニューIDへのアップロード"""
        image_file = create_test_image(format='JPEG')
        files = {"file": ("test.jpg", image_file, "image/jpeg")}
        
        response = client.post(
            "/api/store/menus/99999/image",
            files=files,
            headers=auth_headers_store1
        )
        
        assert response.status_code == 404
        assert "Menu not found" in response.json()["detail"]

    def test_upload_menu_image_unauthorized(self, client, test_db):
        """異常系: 未認証ユーザーのアップロード"""
        image_file = create_test_image(format='JPEG')
        files = {"file": ("test.jpg", image_file, "image/jpeg")}
        
        response = client.post(
            "/api/store/menus/1/image",
            files=files
        )
        
        assert response.status_code == 401


class TestMenuImageDelete:
    """メニュー画像削除のテスト"""

    def test_delete_menu_image_success(self, client, test_db, auth_headers_store1):
        """正常系: 画像の削除"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        menu_id = response.json()["id"]

        # 画像をアップロード
        image_file = create_test_image(format='JPEG')
        files = {"file": ("test.jpg", image_file, "image/jpeg")}
        response = client.post(
            f"/api/store/menus/{menu_id}/image",
            files=files,
            headers=auth_headers_store1
        )
        assert response.status_code == 200
        image_url = response.json()["image_url"]
        image_path = Path(image_url.lstrip('/'))
        assert image_path.exists()

        # 画像を削除
        response = client.delete(
            f"/api/store/menus/{menu_id}/image",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] is None

        # ファイルが削除されていることを確認
        assert not image_path.exists()

    def test_delete_menu_image_no_image(self, client, test_db, auth_headers_store1):
        """正常系: 画像がないメニューの削除（エラーにならない）"""
        # メニューを作成（画像なし）
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "is_available": True
        }
        response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
        menu_id = response.json()["id"]

        # 画像を削除
        response = client.delete(
            f"/api/store/menus/{menu_id}/image",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] is None

    def test_delete_menu_image_menu_not_found(self, client, test_db, auth_headers_store1):
        """異常系: 存在しないメニューの画像削除"""
        response = client.delete(
            "/api/store/menus/99999/image",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 404
        assert "Menu not found" in response.json()["detail"]

    def test_delete_menu_image_unauthorized(self, client, test_db):
        """異常系: 未認証ユーザーの画像削除"""
        response = client.delete("/api/store/menus/1/image")
        assert response.status_code == 401

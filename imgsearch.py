from db import Database

from firstlaunchhandler import default_pictures_dir

# database = Database
# print(default_pictures_dir())

# print(database.scan_folders(database, folders=[default_pictures_dir()]))
def test_list_folders():
    with Database() as db:
        # print(db.scan_folders(folders=[default_pictures_dir()]))
        db.scan_folders(folders=[default_pictures_dir()])
        return db.list_images()
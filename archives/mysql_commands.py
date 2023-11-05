# cursor.execute('CREATE TABLE user (email varchar(255) PRIMARY KEY, user_key varchar(25) )')

# cursor.execute('''
#     CREATE TABLE songs (
#         song_name TEXT,
#         song_url TEXT,
#         email varchar(255),
#         FOREIGN KEY (email) REFERENCES user(email)
#     )
# ''')
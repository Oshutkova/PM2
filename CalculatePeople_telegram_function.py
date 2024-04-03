import os
import psycopg2

host_ = '109.71.243.170'
database_ = 'calc_people_camera'
user_ = 'gen_user'
password_ = 'rftk56^67'
port_ = '5432'

# включаем пользователя в список
def insert_user_into_spisok(message):
    conn = psycopg2.connect(
        host=host_,
        database=database_,
        user=user_,
        password=password_,
        port=port_
        )

    sql = f"""do $$
               declare id1 integer;
               declare tg_username1 varchar;
               begin
                 id1:= null;
                 select id, tg_username into id1, tg_username1
                 from tg_users where tg_id = '{message.from_user.id}';

                if id1 is null then
                  insert into tg_users(tg_id, tg_username)
                              values ({message.from_user.id},
                                      '{message.from_user.username}');
                end if;

                if id1 is not null and tg_username1 <>
                                    '{message.from_user.username}' then
                     update tg_users set tg_username =
                                     '{message.from_user.username}'
                     where id = id1;
                end if;

                end $$;   """

    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


# выводим список объектов
def get_spisok_kamer():
    # параметры соединения с базой
    conn = psycopg2.connect(
        host=host_,
        database=database_,
        user=user_,
        password=password_,
        port=port_
        )

    sql = 'select id, name, url from calc_people_camera order by id'
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    sOut = ''
    for row in rows:
        if row[0] is not None and row[1] is not None:
            if sOut != '':
                sOut += '\n'
            sOut += str(row[0]) + ' - ' + row[1]

    cur.close()
    conn.close()

    return sOut


# выводим список фото объектов
def get_photos_kamer(bot, message):
    # параметры соединения с базой
    conn = psycopg2.connect(
        host=host_,
        database=database_,
        user=user_,
        password=password_,
        port=port_
        )

    sql = """ select C.id, C.name, t_photo.cnt_people, t_photo.date_time,
                     t_photo.folder_name || '/' || t_photo.file_name
              from public.calc_people_camera C
              left join (select tc.id_calc_people_camera, max(id) id_max
                         from calc_people_camera_cnt_people tc
                         group by tc.id_calc_people_camera) t_last_id on
                      t_last_id.id_calc_people_camera = C.id
              left join calc_people_camera_cnt_people t_photo on
                      t_photo.id = t_last_id.id_max
              """
    if message.text.lower() not in ['*', 'all', 'все', 'всё']:
        sql += f""" WHERE C.id = {message.text} """
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    sOut = ''
    if len(rows) == 0:
        sOut = 'Записи отсутсвуют - указан неверный номер'
        bot.send_message(message.chat.id, sOut, parse_mode='html')
    for row in rows:
        if row[0] is not None and row[1] is not None:
            sOut = str(row[0]) + ' - ' + row[1]
            if row[2] is not None and row[3] is not None:
                sOut += ' кол-во лиц ' + str(row[2]) + \
                        ' снято ' + str(row[3].strftime("%d.%m.%Y %H:%M:%S"))
            else:
                sOut += ' не считалось'

            bot.send_message(message.chat.id, sOut, parse_mode='html')

            if row[4] is not None:
                file_name = row[4]
                if os.path.exists(file_name):
                    photo = open(file_name, 'rb')
                    bot.send_photo(message.chat.id, photo)
                else:
                    sOut = 'фото отсутствует'
                    bot.send_message(message.chat.id, sOut, parse_mode='html')
            else:
                sOut = 'фото отсутствует'
                bot.send_message(message.chat.id, sOut, parse_mode='html')
    cur.close()
    conn.close()

    return sOut


# проверка - является ли числом
def is_number(test_value):
    test_value = str(test_value)
    if test_value.isdigit():
        return True
    if len(test_value) > 1:
        if test_value[0].startswith('-') and test_value[1:].isdigit():
            return True
    try:
        float(test_value)  # Пробуем преобразовать строку в число
        return True
    except ValueError:
        return False



import os
import cv2
import telebot
import numpy as np
import psycopg2
from datetime import datetime
import time
import requests
import shutil

host_ = '109.71.243.170'
database_ = 'calc_people_camera'
user_ = 'gen_user'
password_ = 'rftk56^67'
port_ = '5432'

TOKEN = '7067388213:AAEWGOHb1uOzmlOzczYbKYx8_D5IG57W6rs'
bot = telebot.TeleBot(TOKEN)


class Konstant_class:
    name = ''
    value = ''


class Kamera_class:
    id = 0
    name = ''
    url = ''
    usl_send_less = 0   # сообщение уйдёт если значение будет меньше заданного
    usl_send_more = 0   # сообщение уйдёт если значение будет больше заданного
    usl_change_min = 0  # ухудшение ситуации на величину
    usl_norm_less = 0   # нормализация условий после снижения
    usl_norm_more = 0   # нормализация условий псле превышения
    cnt_people = 0      # сколько человек определено на картинке
    folder_name = ''    # папка куда загружен файл
    file_name = ''      # имя загруженного файла с картинкой
    file_name_obr = ''  # имя обработанного фала (расчерчены люди)
    # условия на превышение
    last_send_more_usl_dt = datetime.now()   # дата/вр посл сообщ по условиям
    last_send_more_usl_cnt = 0   # количество людей в последнем сообщении
    last_send_more_norm_dt = datetime.now()  # дата/вр посл сообщ по нормал
    last_send_more_norm_cnt = 0  # кол-во лиц в последнем сообщении по нормал
    # условия на снижение
    last_send_less_usl_dt = datetime.now()   # дата/вр посл сообщ по условиям
    last_send_less_usl_cnt = 0   # количество людей в последнем сообщении
    last_send_less_norm_dt = datetime.now()  # дата/вр посл сообщ по нормал
    last_send_less_norm_cnt = 0  # кол-во лиц в последнем сообщении по нормал
    # Создать сообщения для услолвия превышения:
    b_add_mess_usl_more = 0       # создать сообщение для условия превышения
    b_add_mess_usl_more_norm = 0  # создать сообщение о нормализации
    # Создать сообщения для услолвия снижения:
    b_add_mess_usl_less = 0       # создать сообщение для условия превышения
    b_add_mess_usl_less_norm = 0  # создать сообщение о нормализации


# функция по выделению людей на картинке
def find_people(kamera):
    # Загрузка модели и весов YOLOv3
    net = cv2.dnn.readNet("yolov3.weights", "darknet/cfg/yolov3.cfg")
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

    # Загрузка изображения
    image = cv2.imread(kamera.folder_name + '/' + kamera.file_name)
    height, width, channels = image.shape

    # Подготовка изображения для детекции
    blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0),
                                 True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    # Обнаружение объектов на изображении
    class_ids = []
    confidences = []
    boxes = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            # Проверка на наличие класса человека
            # 0 - класс человека
            # 0,5 - вероятность выше 0,5
            if confidence > 0.5 and class_id == 0:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Отрисовка рамки вокруг людей на изображении
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    font = cv2.FONT_HERSHEY_PLAIN
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(image, 'Person', (x, y), font, 1, (255, 255, 255), 1)

    kamera.cnt_people = len(indexes)

    # Сохраняем изображение
    file_name_new = kamera.file_name[:-4] + '__' + str(kamera.cnt_people)
    prefix = ''
    i = 0
    while os.path.exists(kamera.folder_name + '/' +
                         file_name_new + prefix + '.jpg'):
        i += 1
        prefix = '_' + str(i)

    kamera.file_name_obr = file_name_new + prefix + '.jpg'
    cv2.imwrite(kamera.folder_name + '/' + kamera.file_name_obr, image)

    kamera.file_name_obr = kamera.file_name_obr


# проверка является ли значение числом
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


# РАБОТА С КОНСТАНТАМИ
# получаем все константы из базы
def get_all_konstant(conn):
    konstants = []
    cur = conn.cursor()
    sql = """ select name, value
                 from public.calc_people_camera_param
                 """

    cur.execute(sql)
    conn.commit()
    rows = cur.fetchall()
    for row in rows:
        konstant = Konstant_class()
        konstant.name = row[0]
        konstant.value = row[1]
        konstants.append(konstant)
    cur.close()

    return konstants


# получаем значене константы
# type_out 1 - строка, 2 - число, 3 - дата
def get_konstant(konstant_name, konstants, type_out):
    for konstant in konstants:
        if konstant_name == konstant.name:
            if type_out == 1:
                return konstant.value
            elif type_out == 2:
                if is_number(konstant.value):
                    return int(konstant.value)
            elif type_out == 3:
                try:
                    return datetime.strptime(konstant.value, '%d.%m.%Y')
                except Exception as e:
                    print(f"Ошибка преобразования в дату: {e}")
                    return ''
    return ''


# Получаем список опрашиваемых камер
def get_spisok_kamer(conn):
    kameras = []
    cur = conn.cursor()
    sql = """
        select C.id, C.name, C.url, C.usl_send_less, C.usl_send_more,
               C.usl_change_min, C.usl_norm_less, C.usl_norm_more,
               t_usl_more_last.date_time last_send_more_usl_dt,
               t_usl_more_last.cnt_people last_send_more_usl_cnt,
               t_more_norm_last.date_time last_send_more_norm_dt,
               t_more_norm_last.cnt_people last_send_more_norm_cnt,
               t_usl_less_last.date_time last_send_less_usl_dt,
               t_usl_less_last.cnt_people last_send_less_usl_cnt,
               t_less_norm_last.date_time last_send_less_norm_dt,
               t_less_norm_last.cnt_people last_send_less_norm_cnt
        from calc_people_camera C

        left join (select tc.id_calc_people_camera, max(id) id_max
                     from calc_people_camera_cnt_people tc
                     where tc.b_add_mess_usl_more = True
                     group by tc.id_calc_people_camera) t_usl_more_last_id on
                                t_usl_more_last_id.id_calc_people_camera = C.id
          left join calc_people_camera_cnt_people t_usl_more_last on
                                t_usl_more_last.id = t_usl_more_last_id.id_max

        left join (select tc.id_calc_people_camera, max(id) id_max
                     from calc_people_camera_cnt_people tc
                     where tc.b_add_mess_usl_more_norm = True
                     group by tc.id_calc_people_camera) t_usl_more_norm_id on
                                t_usl_more_norm_id.id_calc_people_camera = C.id
        left join calc_people_camera_cnt_people t_more_norm_last on
                                t_more_norm_last.id = t_usl_more_norm_id.id_max

              left join (select tc.id_calc_people_camera, max(id) id_max
                     from calc_people_camera_cnt_people tc
                     where tc.b_add_mess_usl_less = True
                     group by tc.id_calc_people_camera) t_usl_less_last_id on
                                t_usl_less_last_id.id_calc_people_camera = C.id
          left join calc_people_camera_cnt_people t_usl_less_last on
                                t_usl_less_last.id = t_usl_less_last_id.id_max

        left join (select tc.id_calc_people_camera, max(id) id_max
                     from calc_people_camera_cnt_people tc
                     where tc.b_add_mess_usl_less_norm = True
                     group by tc.id_calc_people_camera) t_usl_less_norm_id on
                                t_usl_less_norm_id.id_calc_people_camera = C.id
          left join calc_people_camera_cnt_people t_less_norm_last on
                                t_less_norm_last.id = t_usl_less_norm_id.id_max
        """

    cur.execute(sql)
    rows = cur.fetchall()
    for row in rows:
        kamera = Kamera_class()
        kamera.id = row[0]
        kamera.name = row[1]
        kamera.url = row[2]
        if row[3] is not None:
            kamera.usl_send_less = row[3]
        else:
            kamera.usl_send_less = -1
        if row[4] is not None:
            kamera.usl_send_more = row[4]
        else:
            kamera.usl_send_more = -1
        if row[5] is not None:
            kamera.usl_change_min = row[5]
        else:
            kamera.usl_change_min = -1

        if row[6] is not None:
            kamera.usl_norm_less = row[6]
        else:
            kamera.usl_norm_less = -1

        if row[7] is not None:
            kamera.usl_norm_more = row[7]
        else:
            kamera.usl_norm_more = -1

        if row[8] is not None:
            kamera.last_send_more_usl_dt = row[8]
        else:
            kamera.last_send_more_usl_dt = datetime(1900, 1, 1)

        if row[9] is not None:
            kamera.last_send_more_usl_cnt = row[9]
        else:
            kamera.last_send_more_usl_cnt = -1

        if row[10] is not None:
            kamera.last_send_more_norm_dt = row[10]
        else:
            kamera.last_send_more_norm_dt = datetime(1900, 1, 1)

        if row[11] is not None:
            kamera.last_send_more_norm_cnt = row[11]
        else:
            kamera.last_send_more_norm_cnt = -1

        if row[12] is not None:
            kamera.last_send_less_usl_dt = row[12]
        else:
            kamera.last_send_less_usl_dt = datetime(1900, 1, 1)

        if row[13] is not None:
            kamera.last_send_less_usl_cnt = row[13]
        else:
            kamera.last_send_less_usl_cnt = -1

        if row[14] is not None:
            kamera.last_send_less_norm_dt = row[14]
        else:
            kamera.last_send_less_norm_dt = datetime(1900, 1, 1)

        if row[15] is not None:
            kamera.last_send_less_norm_cnt = row[15]
        else:
            kamera.last_send_less_norm_cnt = -1

        kameras.append(kamera)
    cur.close()

    return kameras


def add_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)


# копируем картинки с камер на диск
def get_pic_from_camera(spisok_kamer):
    for i, kamera in enumerate(spisok_kamer):
        response = requests.get(kamera.url, stream=True)
        # Проверка успешности запроса
        if response.status_code == 200:
            # Открытие файла для сохранения картинки
            folder_name = 'photo_camera/' + "{:04d}".format(kamera.id)
            add_folder(folder_name)
            file_name = '{:04d}'.format(kamera.id) + '_' + \
                        datetime.now().strftime('%Y-%m-%d__%H_%M_%S') + '.jpg'
            # папка куда загружен файл
            spisok_kamer[i].folder_name = folder_name
            spisok_kamer[i].file_name = file_name
            with open(folder_name + '/' + file_name, 'wb') as file:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, file)


# удаляем файлы картинок при превышении заданного числа
def clear_photo_folder(spisok_kamer, cnt_file):

    for kamera in spisok_kamer:
        files = []
        for item in sorted(os.listdir(kamera.folder_name)):
            if os.path.isfile(kamera.folder_name + '/' + item):
                files.append(kamera.folder_name + '/' + item)
        if len(files) > cnt_file:
            for file in files[:len(files) - cnt_file]:
                print(file)
                os.remove(file)


# проверка условий на необходимость направления сообщений
def usl_send_mess(spisok_kamer, konstants):
    min_inrerval_sec = get_konstant('Мин интервал оповещения - сек',
                                    konstants, 2)

    for i, kam in enumerate(spisok_kamer):
        # сообщение на выполнения условия превышения
        if kam.usl_send_more > 0 and kam.cnt_people > kam.usl_send_more and \
           (
             kam.last_send_more_usl_dt == datetime(1900, 1, 1) or
             (datetime.now() - kam.last_send_more_usl_dt).total_seconds() >
             min_inrerval_sec or
             (kam.last_send_more_norm_dt != datetime(1900, 1, 1) and
              kam.last_send_more_norm_dt > kam.last_send_more_usl_dt) or
             kam.cnt_people > kam.last_send_more_usl_cnt + kam.usl_change_min
           ):
            spisok_kamer[i].b_add_mess_usl_more = 1
        # сообщение на выполнения условия занижения
        if kam.usl_send_less > 0 and kam.cnt_people < kam.usl_send_less and \
           (
             kam.last_send_less_usl_dt == datetime(1900, 1, 1) or
             (datetime.now() - kam.last_send_less_usl_dt).total_seconds() >=
             min_inrerval_sec or
             (kam.last_send_less_norm_dt != datetime(1900, 1, 1) and
              kam.last_send_less_norm_dt > kam.last_send_less_usl_dt) or
             kam.cnt_people < kam.last_send_less_usl_cnt - kam.usl_change_min
           ):
            spisok_kamer[i].b_add_mess_usl_less = 1
        # сообщение на выполнение условия нормализации при превышении
        if kam.usl_send_more > 0 and kam.cnt_people <= kam.usl_norm_more and \
           kam.last_send_more_usl_dt > datetime(1900, 1, 1) and \
           (
             kam.last_send_more_norm_dt == datetime(1900, 1, 1) or
             kam.last_send_more_norm_dt < kam.last_send_more_usl_dt
           ):
            spisok_kamer[i].b_add_mess_usl_more_norm = 1
        # сообщение на выполнение условия нормализации при снижении
        if kam.usl_send_less > 0 and kam.cnt_people >= kam.usl_norm_less and \
           kam.last_send_less_usl_dt > datetime(1900, 1, 1) and \
           (
             kam.last_send_less_norm_dt == datetime(1900, 1, 1) or
             kam.last_send_less_norm_dt < kam.last_send_less_usl_dt
           ):
            spisok_kamer[i].b_add_mess_usl_less_norm = 1


# запись результата анализачисленности в базу
def result_write_base(spisok_kamer, conn):
    for kam in spisok_kamer:
        b_add_mess_usl_more, b_add_mess_usl_more_norm = False, False
        b_add_mess_usl_less, b_add_mess_usl_less_norm = False, False
        if kam.b_add_mess_usl_more == 1:
            b_add_mess_usl_more = True
        if kam.b_add_mess_usl_more_norm == 1:
            b_add_mess_usl_more_norm = True
        if kam.b_add_mess_usl_less == 1:
            b_add_mess_usl_less = True
        if kam.b_add_mess_usl_less_norm == 1:
            b_add_mess_usl_less_norm = True

        sql = f""" INSERT INTO calc_people_camera_cnt_people
                      (id_calc_people_camera, cnt_people, date_time,
                       b_add_mess_usl_more, b_add_mess_usl_more_norm,
                       b_add_mess_usl_less, b_add_mess_usl_less_norm,
                       folder_name, file_name)
                   VALUES
                      ({kam.id}, {kam.cnt_people}, current_timestamp,
                       {b_add_mess_usl_more}, {b_add_mess_usl_more_norm},
                       {b_add_mess_usl_less}, {b_add_mess_usl_less_norm},
                       '{kam.folder_name}', '{kam.file_name_obr}'
                       )   """
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()


# направляем сообщения
def send_message(spisok_kamer, konstants, conn):

    # ищем шв кому отправлять
    tg_user_name = get_konstant('Адресат - Telegramm', konstants, 1)

    cur = conn.cursor()
    sql = f""" select tg_id
                 from public.tg_users
                 where tg_username = '{tg_user_name}'
                 """

    cur.execute(sql)
    conn.commit()
    rows = cur.fetchall()
    if len(rows) > 0:
        tg_id = rows[0][0]
        for kam in spisok_kamer:
            if kam.b_add_mess_usl_more == 1 or \
               kam.b_add_mess_usl_more_norm == 1 or\
               kam.b_add_mess_usl_less == 1 or \
               kam.b_add_mess_usl_less_norm == 1:
                sOut = str(kam.id) + ' - ' + kam.name
                sOut += ' кол-во лиц ' + str(kam.cnt_people)
                if kam.b_add_mess_usl_more == 1:
                    sOut += ' условие превышения'
                if kam.b_add_mess_usl_less == 1:
                    sOut += ' условие снижения'
                if kam.b_add_mess_usl_more_norm == 1:
                    sOut += ' возврат в норму после превышения'
                if kam.b_add_mess_usl_less_norm == 1:
                    sOut += ' возврат в норму после снижения'
                bot.send_message(tg_id, sOut, parse_mode='html')

                file_name = kam.folder_name + '/' + kam.file_name_obr
                if os.path.exists(file_name):
                    photo = open(file_name, 'rb')
                    bot.send_photo(tg_id, photo)
                else:
                    sOut = 'фото отсутствует'
                    bot.send_message(tg_id, sOut, parse_mode='html')

    cur.close()

    return konstants


# точка входа
def main():
    # параметры соединения с базой
    conn = psycopg2.connect(
        host=host_,
        database=database_,
        user=user_,
        password=password_,
        port=port_
        )
    # получаем константы
    konstants = get_all_konstant(conn)

    # получаем список камер (с которых будем брать картинки)
    spisok_kamer = get_spisok_kamer(conn)
    get_pic_from_camera(spisok_kamer)

    # считаем кол-во людей на кадом фото и сохраняем новые картинки
    for i in range(len(spisok_kamer)):
        find_people(spisok_kamer[i])

    # удаляем последние файлы при превышении заданного числа
    cnt_file = get_konstant('Макс число картинок по камере', konstants, 2)
    clear_photo_folder(spisok_kamer, cnt_file)
    # проверка условий на необходимость направления сообщений
    usl_send_mess(spisok_kamer, konstants)
    # собственно направляем сообщения
    send_message(spisok_kamer, konstants, conn)
    # записываем результата в базу
    result_write_base(spisok_kamer, conn)

    conn.close()

    # спать - и снова в работу (чтобы не замучить камеры и базу)
    sec_sleep = get_konstant('Периодичность опроса - сек', konstants, 2)
    time.sleep(sec_sleep)


main()

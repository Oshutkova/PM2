% git branch testing
# подключаем модуль для автотестов
import unittest

from CalculatePeople import find_people as fp
from CalculatePeople import result_write_base as rws

# объявляем класс с тестом
class fpTestCase(unittest.TestCase):
    # функция, которая проверит, как формируется обработанная картинка
   def test_fp(kamera):
        # отправляем тестовую строку в функцию
        result = kamera('https://github.com/Oshutkova/PM2/blob/6479d0b1f593e8964e4909bb3c19d746a19b37cc/test/ochered%20(1).jpg')
        # задаём ожидаемый результат
        kamera.assertEqual(result, 'https://github.com/Oshutkova/PM2/blob/6479d0b1f593e8964e4909bb3c19d746a19b37cc/test/ochered%20(1)_1.jpg'.")

# запускаем тестирование
if __kamera__ == '__main__':
    unittest.main() 

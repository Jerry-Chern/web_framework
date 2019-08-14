import time

import pymysql

import config
import secret
from utils import log


def pymysql_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password=secret.mysql_password,
        db=config.db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection


class SQLModel(object):
    # User.all()
    # User.one()
    # join
    # prefetch
    # query = User.select()
    # if a > 1:
    #   query.where(id=1)
    # else:
    #   query.join('session', 'id', 'user_id').where(id=1)
    @classmethod
    def init_db(cls):
        cls.connection = pymysql.connect(
            host='localhost',
            user='root',
            password=secret.mysql_password,
            db=config.db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    @classmethod
    def new(cls, form):
        # cls(form) 相当于 User(form)
        m = cls(form)
        id = cls.insert(m.__dict__)
        m.id = id
        return m

    def __init__(self, form):
        # 因为 id 是数据库给的，所以最开始初始化的时候必须是 None
        self.id = form.get('id', None)

    @classmethod
    def table_name(cls):
        return '`{}`'.format(cls.__name__)

    def __repr__(self):
        """
        作用是得到类的 字符串表达 形式
        """
        name = self.__class__.__name__
        properties = ['{}: ({})'.format(k, v) for k, v in self.__dict__.items()]
        s = '\n'.join(properties)
        return '< {}\n{} >\n'.format(name, s)

    @classmethod
    def select(cls, connection):
        # SELECT * FROM user
        sql_select = 'SELECT * FROM {}'.format(cls.table_name())
        return Query(sql_select, connection, cls)

    @classmethod
    def one(cls, **kwargs):
        connection = pymysql_connection()
        m = cls.select(connection).where(**kwargs).one()
        try:
            connection.commit()
        except Exception as e:
            connection.rollback()
        finally:
            connection.close()
        return m

    @classmethod
    def all(cls, **kwargs):
        connection = pymysql_connection()
        m = cls.select(connection).where(**kwargs).all()
        try:
            connection.commit()
        except Exception as e:
            connection.rollback()
        finally:
            connection.close()
        return m

    @classmethod
    def insert(cls, form):
        connection = pymysql_connection()
        # {
        #     'username': 'jerry',
        #     'password': 123,
        # }
        form.pop('id')
        # INSERT INTO `User` (
        #   `username`, `password`, `email`
        # ) VALUES (
        #   %s, %s, %s
        # )
        sql_keys = ', '.join(['`{}`'.format(k) for k in form.keys()])
        sql_values = ', '.join(['%s'] * len(form))
        sql_insert = 'INSERT INTO {} ({}) VALUES ({})'.format(
            cls.table_name(),
            sql_keys,
            sql_values,
        )
        log('ORM insert <{}>'.format(sql_insert))

        values = tuple(form.values())

        # try:
        #   cursor = cls.connection.cursor()
        #   cursor.execute(sql_insert, values)
        #   _id = cursor.lastrowid
        # finally:
        #   cursor.close()
        with connection.cursor() as cursor:
            cursor.execute(sql_insert, values)
            _id = cursor.lastrowid
        connection.commit()
        connection.close()

        return _id

    @classmethod
    def update(cls, id, **kwargs):
        connection = pymysql_connection()
        # UPDATE
        # 	`User`
        # SET
        # 	`username`=%s, `password`=%s
        # WHERE `id`=%s;
        sql_set = ', '.join(
            ['`{}`=%s'.format(k) for k in kwargs.keys()]
        )
        sql_update = 'UPDATE {} SET {} WHERE `id`=%s'.format(
            cls.table_name(),
            sql_set,
        )
        log('ORM update <{}>'.format(sql_update.replace('\n', ' ')))

        values = list(kwargs.values())
        values.append(id)
        values = tuple(values)

        with connection.cursor() as cursor:
            cursor.execute(sql_update, values)
        connection.commit()
        connection.close()

    @classmethod
    def delete(cls, id):
        connection = pymysql_connection()
        sql_delete = 'DELETE FROM {} WHERE `id`=%s'.format(cls.table_name())
        log('ORM delete <{}>'.format(sql_delete.replace('\n', ' ')))

        with connection.cursor() as cursor:
            cursor.execute(sql_delete, (id,))
        connection.commit()
        connection.close()


class Query(object):
    def __init__(self, raw, connection, model):
        self.query = raw
        self.values = tuple()
        self.connection = connection
        self.model = model

    def where(self, **kwargs):
        if len(kwargs) > 0:
            sql_where = ' AND '.join(
                ['`{}`=%s'.format(k) for k in kwargs.keys()]
            )
            sql_where = '\tWHERE\t{}'.format(sql_where)
            self.query = '{}{}'.format(self.query, sql_where)
        log('ORM where <{}>'.format(self.query))

        self.values = tuple(kwargs.values())

        return self

    def all(self):
        log('ORM all <{}> <{}>'.format(self.query, self.values))

        ms = []
        with self.connection.cursor() as cursor:
            log('ORM execute all <{}>'.format(cursor.mogrify(self.query, self.values)))
            cursor.execute(self.query, self.values)
            result = cursor.fetchall()
            for row in result:
                if self.join_exit():
                    m = row
                else:
                    m = self.model(row)
                ms.append(m)
            return ms

    def one(self):
        self.query = '{} LIMIT 1'.format(self.query)
        log('ORM one <{}> <{}>'.format(self.query, self.values))

        with self.connection.cursor() as cursor:
            log('ORM execute one <{}>'.format(cursor.mogrify(self.query, self.values)))
            cursor.execute(self.query, self.values)
            result = cursor.fetchone()
            if result is None:
                return None
            else:
                if self.join_exit():
                    return result
                else:
                    return self.model(result)

    def join(self, target_model, field, target_field):
        # JOIN topic on user.id=topic.user_id
        target_table = target_model.table_name()
        table = self.model.table_name()
        sql_join = 'JOIN {} on {}.{}={}.{}'.format(
            target_table, table, field, target_table, target_field
        )
        self.query = '{}\t{}'.format(self.query, sql_join)
        return self

    def join_exit(self):
        exist = 'JOIN' in self.query
        return exist
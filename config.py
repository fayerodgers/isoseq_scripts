import os

config={
        'user' : os.environ['MYSQL_USER'],
        'password' : os.environ['MYSQL_PASS'],
        'host' : os.environ['MYSQL_HOST'],
        'database' : 'test_isoseq',
        'port' : os.environ['MYSQL_PORT'],
        'raise_on_warnings': True
}

config_iris={
        'user' : os.environ['MYSQL_USER'],
        'password' : os.environ['MYSQL_PASS'],
        'host' : os.environ['MYSQL_HOST'],
        'database' : 'iris_test',
        'port' : os.environ['MYSQL_PORT'],
        'raise_on_warnings': True
}

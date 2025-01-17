import pymysql as db
import requests
from utils.exception_handdle import write_file


def get_pr_file_info(index, maxNum, owner_name, repo_name, headers):
    # 数据操作部分
    # SQL语句书写
    sql = """
        insert into pr_file(
        pr_number, 
        repo_name, 
        changed_file_name,
        sha, 
        changed_file_status, 
        lines_added_num, 
        lines_deleted_num, 
        lines_changed_num,
        contain_patch, 
        patch_content )
        VALUES( %s,%s,%s, %s,%s, %s,%s, %s,%s, %s )
       """
    select_sql = "select pr_number,repo_name,changed_file_num,pr_url from pr_self where repo_name=\'" + repo_name + """\' order by pr_number"""
    # """
    #     select pr_number,repo_name,changed_file_num,pr_url
    # 	from pr_self
    # 	order by pr_number
    # 	"""

    # 链接云端数据库
    database = db.connect(host='172.19.241.129', port=3306, user='root', password='root', db='pr_second', charset='utf8')
    #database = db.connect(host='127.0.0.1', port=3306, user='root', password='root', db='pr_second', charset='utf8')
    # 创建游标对象
    cursor = database.cursor()
    # 利用游标对象进行操作
    cursor.execute(select_sql)
    data = cursor.fetchall()
    # print(data)
    data_len = data.__len__()
    print(data_len)

    while index < data_len:
        # 取出查询的数据
        pr_number = data[index][0]
        repo_name = data[index][1]
        file_num = data[index][2]
        pr_url = data[index][3]
        if file_num == 0:
            index = index + 1
            continue
        # 拼接url
        file_url = pr_url + "/files?per_page=100&page="
        # 调用url中获取
        maxPage = file_num // 100 + 1
        page = 1
        try:
            while page <= maxPage:
                print("========================" + "第" + str(index) + "号 pr_number: " + str(pr_number) + " 第" + str(
                    page) + "页" + "==========================")
                print(pr_number)
                print(repo_name)
                print(file_num)
                temp_url_str = file_url + page.__str__()
                print(temp_url_str)
                url_r = requests.get(temp_url_str, headers=headers)
                print("url_r: " + temp_url_str + "  Status Code:", url_r.status_code)
                files_json = url_r.json()
                # print(files_json)
                # 遍历整个100行大json，然后逐一放入数据库中即可
                temp_file_len = files_json.__len__()
                temp_index = 0
                # 当某个页面没有了数据之后，其后面的页面也没有数据
                if temp_file_len == 0:
                    break
                while temp_index < temp_file_len:
                    try:
                        sqlData = (
                            pr_number,
                            repo_name,
                            files_json[temp_index]["filename"],
                            files_json[temp_index]["sha"],
                            files_json[temp_index]["status"],
                            files_json[temp_index]["additions"],
                            files_json[temp_index]["deletions"],
                            files_json[temp_index]["changes"],
                            ((files_json[temp_index].__contains__("patch") == True) and 1 or 0),
                            ((files_json[temp_index].__contains__("patch") == True) and files_json[temp_index].get(
                                "patch") or None))
                        # 执行sql语句
                        cursor.execute(sql, sqlData)
                        # 提交到数据库执行
                        database.commit()
                        print("第" + str(index) + "号 pr_number: " + str(pr_number) + " 第" + str(page) + "页的第" + str(
                            temp_index) + "个数据插入成功")
                        temp_index = temp_index + 1
                    except Exception as e:
                        # 如果发生错误则回滚
                        print("第" + str(index) + "号 pr_number: " + str(pr_number) + " 第" + str(page) + "页的第" + str(
                            temp_index) + "个数据插入数据库失败: " + str(e))
                        # 当出现重复key时应当可以继续往下走，取下一条数据
                        if e.args[0] == 1062 or e.args[1].__contains__("Duplicate"):
                            temp_index = temp_index + 1
                            continue
                        filename = repo_name + '_file_exception.csv'
                        write_file(index, "user", (
                                "第" + str(index) + "号 pr_number: " + str(pr_number) + " 第" + str(page) + "页的第" + str(
                            temp_index) + "个数据插入数据库失败: " + str(e)), filename)
                        print(e)
                        # traceback.print_exc()
                        database.rollback()
                        break
                page = page + 1

        except Exception as e:
            filename = repo_name + '_file_exception.csv'
            write_file(index, "user", ("第" + str(index) + "号 pr_number: " + str(pr_number) + " 对应的失败: " + str(e)), filename)
            print(e)
            break
        index = index + 1
    # 关闭数据库连接
    database.close()

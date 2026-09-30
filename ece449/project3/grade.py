import traceback
import multiprocessing

def grade_all(name, begin, end, funcs):
    grade = 0
    for q in range(begin, end):
        def func():
            exit(0 if funcs["grade_Q%d" % q]() else 1)
        try:
            p = multiprocessing.Process(target = func)
            p.start()
            p.join(300)
            if p.is_alive():
                p.terminate()
                print("============Q%d timeout!============\n" % q, flush = True)
            elif p.exitcode == 0:
                print("============Q%d passed!============\n" % q, flush = True)
                grade += 1
            else:
                print("============Q%d failed!============\n" % q, flush = True)
        except Exception as e:
            print("============Q%d failed!============" % q, flush = True)
            print(traceback.format_exc())
    print("Grading result: %d functions passed" % grade)
    
    print("************************************************************-*")
    print("* You may receive 0 points unless your code tests correctly  *")
    print("* Do not forget to 'git add .', 'git commit', then 'git push'*")
    print("* Please commit and push your code at least daily.           *")
    print("* DO NOT CHANGE any grade_px.py for grading                  *")
    print("************************************************************-*")

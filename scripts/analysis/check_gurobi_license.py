import gurobipy as gp

print("gurobipy", gp.gurobi.version())
environment = gp.Env(empty=True)
environment.setParam("OutputFlag", 0)
environment.start()
print("LICENSE_OK")

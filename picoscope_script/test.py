import numpy as np

arr = np.array([0,1,2,3,4,5,6,7]*32)
arr_reshape = arr.reshape(-1,32)
arr_f = np.mean(arr_reshape,1)

print(arr_f)

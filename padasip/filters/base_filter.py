"""
.. versionadded:: 0.1
.. versionchanged:: 1.2.0

"""
import numpy as np

from padasip.misc import get_mean_error

class AdaptiveFilter():
    """
    Base class for adaptive filter classes. It puts together some functions
    used by all adaptive filters.
    """
    def __init__(self, mu, n, w="random"):
        """
        This class represents an generic adaptive filter.

        **Args:**

        * `n` : length of filter (integer) - how many input is input array
          (row of input matrix)

        **Kwargs:**

        * `mu` : learning rate (float). Also known as step size. If it is too slow,
          the filter may have bad performance. If it is too high,
          the filter will be unstable. The default value can be unstable
          for ill-conditioned input data.

        * `w` : initial weights of filter. Possible values are:

            * array with initial weights (1 dimensional array) of filter size

            * "random" : create random weights

            * "zeros" : create zero value weights
        """
        self.w = self.init_weights(w, n)
        self.n = n
        self.w_history = False
        self.mu = mu

    def init_weights(self, w, n=-1):
        """
        This function initialises the adaptive weights of the filter.

        **Args:**

        * `w` : initial weights of filter. Possible values are:
        
            * array with initial weights (1 dimensional array) of filter size
        
            * "random" : create random weights
            
            * "zeros" : create zero value weights


        **Kwargs:**

        * `n` : size of filter (int) - number of filter coefficients.

        **Returns:**

        * `y` : output value (float) calculated from input array.

        """
        if n == -1:
            n = self.n
        if type(w) == str:
            if w == "random":
                w = np.random.normal(0, 0.5, n)
            elif w == "zeros":
                w = np.zeros(n)
            else:
                raise ValueError('Impossible to understand the w')
        elif len(w) == n:
            try:
                w = np.array(w, dtype="float64")
            except:
                raise ValueError('Impossible to understand the w')
        else:
            raise ValueError('Impossible to understand the w')
        return w

    def predict(self, x):
        """
        This function calculates the new output value `y` from input array `x`.

        **Args:**

        * `x` : input vector (1 dimension array) in length of filter.

        **Returns:**

        * `y` : output value (float) calculated from input array.

        """
        return np.dot(self.w, x)

    def pretrained_run(self, d, x, ntrain=0.5, epochs=1):
        """
        This function sacrifices part of the data for few epochs of learning.
        
        **Args:**

        * `d` : desired value (1 dimensional array)

        * `x` : input matrix (2-dimensional array). Rows are samples,
          columns are input arrays.
       
        **Kwargs:**

        * `ntrain` : train to test ratio (float), default value is 0.5
          (that means 50% of data is used for training)
          
        * `epochs` : number of training epochs (int), default value is 1.
          This number describes how many times the training will be repeated
          on dedicated part of data.

        **Returns:**
        
        * `y` : output value (1 dimensional array).
          The size corresponds with the desired value.

        * `e` : filter error for every sample (1 dimensional array).
          The size corresponds with the desired value.

        * `w` : vector of final weights (1 dimensional array).    
        """
        Ntrain = int(len(d)*ntrain)
        # train
        for epoch in range(epochs):
            self.run(d[:Ntrain], x[:Ntrain])
        # test
        y, e, w = self.run(d[Ntrain:], x[Ntrain:])
        return y, e, w

    def adapt(self, d, x):
        """
        Adapt weights according one desired value and its input.

        **Args:**

        * `d` : desired value (float)

        * `x` : input array (1-dimensional array)
        """
        y = self.predict(x)
        e = d - y
        self.w += learning_rule(self, e, x)

    def run(self, d, x):
        """
        This function filters multiple samples in a row.

        **Args:**

        * `d` : desired value (1 dimensional array)

        * `x` : input matrix (2-dimensional array). Rows are samples,
          columns are input arrays.

        **Returns:**

        * `y` : output value (1 dimensional array).
          The size corresponds with the desired value.

        * `e` : filter error for every sample (1 dimensional array).
          The size corresponds with the desired value.

        * `w` : history of all weights (2 dimensional array).
          Every row is set of the weights for given sample.
        """
        # measure the data and check if the dimension agree
        N = len(x)
        if not len(d) == N:
            raise ValueError('The length of vector d and matrix x must agree.')
        self.n = len(x[0])
        # prepare data
        try:
            x = np.array(x)
            d = np.array(d)
        except:
            raise ValueError('Impossible to convert x or d to a numpy array')
        # create empty arrays
        y = np.zeros(N)
        e = np.zeros(N)
        self.w_history = np.zeros((N,self.n))
        # adaptation loop
        for k in range(N):
            self.w_history[k,:] = self.w
            y[k] = self.predict(x[k])
            e[k] = d[k] - y[k]
            self.w += self.learning_rule(e[k], x[k])
        return y, e, self.w_history


class AdaptiveFilterAP(AdaptiveFilter):
    """
    Adaptive AP filter.

    **Kwargs:**

    * `order` : projection order (integer) - how many input vectors
      are in one input matrix

    * `eps` : initial offset covariance (float)

    """
    def __init__(self, *args, order=5, eps=0.001, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
        self.eps = eps
        self.x_mem = np.zeros((self.n, self.order))
        self.d_mem = np.zeros(order)
        self.ide_eps = self.eps * np.identity(self.order)
        self.ide = np.identity(self.order)
        self.y_mem = False
        self.e_mem = False

    def adapt(self, d, x):
        """
        Adapt weights according one desired value and its input.

        **Args:**

        * `d` : desired value (float)

        * `x` : input array (1-dimensional array)
        """
        # create input matrix and target vector
        self.x_mem[:, 1:] = self.x_mem[:, :-1]
        self.x_mem[:, 0] = x
        self.d_mem[1:] = self.d_mem[:-1]
        self.d_mem[0] = d
        # estimate output and error
        self.y_mem = np.dot(self.x_mem.T, self.w)
        self.e_mem = self.d_mem - self.y_mem
        # update
        dw_part1 = np.dot(self.x_mem.T, self.x_mem) + self.ide_eps
        dw_part2 = np.linalg.solve(dw_part1, self.ide)
        dw = np.dot(self.x_mem, np.dot(dw_part2, self.e_mem))
        self.w += self.mu * dw

    def run(self, d, x):
        """
        This function filters multiple samples in a row.

        **Args:**

        * `d` : desired value (1 dimensional array)

        * `x` : input matrix (2-dimensional array). Rows are samples,
          columns are input arrays.

        **Returns:**

        * `y` : output value (1 dimensional array).
          The size corresponds with the desired value.

        * `e` : filter error for every sample (1 dimensional array).
          The size corresponds with the desired value.

        * `w` : history of all weights (2 dimensional array).
          Every row is set of the weights for given sample.

        """
        # measure the data and check if the dimmension agree
        N = len(x)
        if not len(d) == N:
            raise ValueError('The length of vector d and matrix x must agree.')
        self.n = len(x[0])
        # prepare data
        try:
            x = np.array(x)
            d = np.array(d)
        except:
            raise ValueError('Impossible to convert x or d to a numpy array')
        # create empty arrays
        y = np.zeros(N)
        e = np.zeros(N)
        self.w_history = np.zeros((N, self.n))
        # adaptation loop
        for k in range(N):
            self.w_history[k, :] = self.w
            # create input matrix and target vector
            self.x_mem[:, 1:] = self.x_mem[:, :-1]
            self.x_mem[:, 0] = x[k]
            self.d_mem[1:] = self.d_mem[:-1]
            self.d_mem[0] = d[k]
            # estimate output and error
            self.y_mem = np.dot(self.x_mem.T, self.w)
            self.e_mem = self.d_mem - self.y_mem
            y[k] = self.y_mem[0]
            e[k] = self.e_mem[0]
            # update
            self.w += self.learning_rule(self.e_mem, self.x_mem)
        return y, e, self.w_history

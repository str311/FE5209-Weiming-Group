"""True ERC via convex risk budgeting, with deterministic Newton refinement."""
import numpy as np
from scipy.optimize import minimize

def risk_contributions(weights,cov):
    w=np.asarray(weights,dtype=float)
    var=float(w@cov@w)
    if var<=0: raise ValueError('Nonpositive portfolio variance')
    rc=w*(cov@w)/np.sqrt(var)
    return rc,rc/np.sqrt(var)


def erc_weights(cov):
    # Convex risk-budget formulation: x_i(Sigma x)_i=b_i; normalize x afterwards.
    # Scaling covariance by a positive scalar does not change portfolio weights.
    S=np.asarray(cov,dtype=float)/np.mean(np.diag(cov))
    n=len(S); b=np.full(n,1/n)
    def fun(x): return .5*x@S@x-np.dot(b,np.log(x))
    def jac(x): return S@x-b/x
    initial=np.sqrt(b/np.diag(S))
    fit=minimize(fun,initial,jac=jac,method='L-BFGS-B',bounds=[(1e-10,None)]*n,
                 options={'ftol':1e-15,'gtol':1e-11,'maxiter':2000,'maxls':60})
    x=fit.x
    # A deterministic Newton polish addresses objective-rounding termination,
    # not any economic parameter or performance optimization.
    for _ in range(12):
        g=jac(x)
        if np.max(np.abs(g))<1e-12: break
        delta=np.linalg.solve(S+np.diag(b/x**2),-g)
        step=min(1.0,min((-0.99*x[delta<0]/delta[delta<0]),default=1.0))
        for _ in range(40):
            trial=x+step*delta
            if np.all(trial>0) and fun(trial)<=fun(x)+1e-4*step*np.dot(g,delta)+1e-15:
                x=trial; break
            step*=.5
        else: break
    w=x/x.sum(); _,fraction=risk_contributions(w,cov)
    error=float(np.max(np.abs(fraction-1/n)))
    if error>1e-7: raise RuntimeError(f'ERC solver budget error {error}; {fit.message}')
    return w,error,int(fit.nit)



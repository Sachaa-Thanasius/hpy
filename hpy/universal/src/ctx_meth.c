#include "ctx_meth.h"
#include "handles.h"

HPyAPI_STORAGE struct _object *
ctx_CallRealFunctionFromTrampoline(HPyContext ctx, struct _object *self,
                                   struct _object *args, struct _object *kw,
                                   void *func, HPyMeth_Signature sig)
{
    switch (sig) {
    case HPyMeth_NOARGS: {
        HPyMeth_noargs f = (HPyMeth_noargs)func;
        return _h2py(f(ctx, _py2h(self)));
    }
    case HPyMeth_O: {
        HPyMeth_o f = (HPyMeth_o)func;
        return _h2py(f(ctx, _py2h(self), _py2h(args)));
    }
    case HPyMeth_VARARGS: {
        HPyMeth_varargs f = (HPyMeth_varargs)func;
        Py_ssize_t nargs = PyTuple_GET_SIZE(args);
        HPy *h_args = alloca(nargs * sizeof(HPy));
        for (Py_ssize_t i = 0; i < nargs; i++) {
            h_args[i] = _py2h(PyTuple_GET_ITEM(args, i));
        }
        return _h2py(f(ctx, _py2h(self), h_args, nargs));
    }
    /*
    case HPy_METH_KEYWORDS: {
       HPyMeth_Keywords f = (HPyMeth_Keywords)func;
       Py_ssize_t nargs = PyTuple_GET_SIZE(args);
       HPy *h_args = alloca(nargs * sizeof(HPy));
       for (Py_ssize_t i = 0; i < nargs; i++) {
           h_args[i] = _py2h(PyTuple_GET_ITEM(args, i));
       }
       return _h2py(f(ctx, _py2h(self), h_args, nargs, _py2h(kw)));
    }
    */
    default:
        abort();  // XXX
    }
}

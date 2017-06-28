
/*
Based on a significant portion of CPython's dictobject code.
*/

#include <sys/mman.h>
#include <fcntl.h>
#include <Python.h>
#include "bytesobject.h"
#include "structmember.h"

#define PERTURB_SHIFT    5
#define BUCKET_SIZE      4


typedef struct {
    uint32_t chunk_pointer;
} Bucket;


typedef struct {
    uint16_t key_len;
    uint16_t value_len;
    char data;
} Chunk;


typedef struct {
    PyObject_HEAD
    size_t size;
    char *buf;
    int num_buckets;
    Bucket *bucket0;
    char *payload;
} LrmObject;


static PyObject *DirtyError;


static long string_hash(PyBytesObject *a) {
    register Py_ssize_t len;
    register unsigned char *p;
    register long x;

    len = Py_SIZE(a);
    if (len == 0) {
        return 0;
    }
    p = (unsigned char *)a->ob_sval;
    x = *p << 7;
    while (--len >= 0) {
        x = (1000003 * x) ^ *p++;
    }
    x ^= Py_SIZE(a);
    return x;
}


static PyObject *stable_hash(PyObject *self, PyObject *args) {
    PyBytesObject *string;

    if (! PyArg_ParseTuple(args, "S", &string))
        return NULL;

    long hash = string_hash(string);
    return Py_BuildValue("l", hash);
}


static void Lrm_dealloc(LrmObject *self) {
    munmap(self->buf, self->size);
    Py_TYPE(self)->tp_free((PyObject *)self);
}


static PyObject *Lrm_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    LrmObject *self;

    self = (LrmObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->size = 0;
        self->buf = NULL;
        self->num_buckets = 0;
        self->bucket0 = NULL;
        self->payload = NULL;
    }

    return (PyObject *)self;
}


static int Lrm_init(LrmObject *self, PyObject *args, PyObject *kwds) {
    char *filepath;
    int fd;
    uint32_t num_buckets;

    if (! PyArg_ParseTuple(args, "s", &filepath))
        return -1;

    fd = open(filepath, O_RDONLY);
    if (fd < 0) {
        PyErr_SetString(PyExc_ValueError, "Can't open file.");
        return -1;
    }

    self->size = lseek(fd, 0, SEEK_END);
    self->buf = mmap(NULL, self->size, PROT_READ, MAP_SHARED, fd, 0);

    close(fd);

    if (self->buf == MAP_FAILED) {
        PyErr_SetString(PyExc_OSError, "Can't create mmap.");
        return -1;
    }

    if (strncmp(self->buf, "LEDD", 4) == 0) {
        PyErr_SetString(DirtyError, "File is dirty.");
        return -1;
    }

    if (strncmp(self->buf, "LEDA", 4) != 0) {
        PyErr_SetString(PyExc_ValueError, "Incorrect file format.");
        return -1;
    }

    memcpy(&num_buckets, self->buf + 4, 4);
    self->num_buckets = num_buckets;
    self->bucket0 = (Bucket *)(self->buf + 8);
    self->payload = (char *)(self->bucket0 + num_buckets * BUCKET_SIZE);
    return 0;
}


static PyObject *Lrm_get(LrmObject *self, PyObject *args) {
    char *name_str;
    PyObject *name;
    register size_t idx;
    register size_t perturb;
    register size_t mask;
    Bucket *bucket0 = self->bucket0;
    register Bucket *bucket;
    register volatile char *vbuf;

    if (! PyArg_ParseTuple(args, "S", &name)) {
        return NULL;
    }

    vbuf = self->buf;
    if (vbuf[3] == 'D') {
        PyErr_SetString(DirtyError, "File is dirty.");
        return NULL;
    }

    name_str = PyBytes_AsString(name);

    mask = self->num_buckets - 1;
    long hash = string_hash((PyBytesObject *)name);
    idx = (size_t)hash & mask;
    perturb = hash;

    while (1) {
        bucket = &bucket0[idx];
        if (bucket->chunk_pointer == 0) {
            Py_INCREF(Py_None);
            return Py_None;
        }

        register Py_ssize_t name_size;
        register Chunk *chunk;

        name_size = PyBytes_GET_SIZE(name);
        chunk = (Chunk *)(self->buf + bucket->chunk_pointer);

        if ((name_size == chunk->key_len) && (strncmp(&chunk->data, name_str, chunk->key_len) == 0)) {
            return PyBytes_FromStringAndSize(&chunk->data + chunk->key_len, chunk->value_len);
        }

        idx = (idx << 2) + idx + perturb + 1;
        perturb >>= PERTURB_SHIFT;
        idx &= mask;
    }
}


static PyObject *Lrm_uget(LrmObject *self, PyObject *args) {
    register PyObject *result;

    result = Lrm_get(self, args);
    if (result == NULL) {
        return NULL;
    }

    if (result == Py_None) {
        return result;
    }

    return PyUnicode_FromEncodedObject(result, "utf8", NULL);
}


static PyMemberDef Lrm_members[] = {
    {NULL}
};


static PyMethodDef Lrm_methods[] = {
    {"get", (PyCFunction)Lrm_get, METH_VARARGS, "Return value by key, otherwise None if not found"},
    {"uget", (PyCFunction)Lrm_uget, METH_VARARGS, "Return value by key (as unicode object), otherwise None if not found"},
    {NULL}
};


static PyMethodDef Module_methods[] = {
    {"stable_hash", (PyCFunction)stable_hash, METH_VARARGS, "Return stable hash (without randomization) for given string"},
    {NULL}
};


static PyTypeObject LrmType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "cledadamap.LedadaReadMap",     /*tp_name*/
    sizeof(LrmObject),              /*tp_basicsize*/
    0,                              /*tp_itemsize*/
    (destructor)Lrm_dealloc,        /*tp_dealloc*/
    0,                              /*tp_print*/
    0,                              /*tp_getattr*/
    0,                              /*tp_setattr*/
    0,                              /*tp_compare*/
    0,                              /*tp_repr*/
    0,                              /*tp_as_number*/
    0,                              /*tp_as_sequence*/
    0,                              /*tp_as_mapping*/
    0,                              /*tp_hash */
    0,                              /*tp_call*/
    0,                              /*tp_str*/
    0,                              /*tp_getattro*/
    0,                              /*tp_setattro*/
    0,                              /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,             /*tp_flags*/
    "ledada read-only hash map",    /* tp_doc */
    0,                              /* tp_traverse */
    0,                              /* tp_clear */
    0,                              /* tp_richcompare */
    0,                              /* tp_weaklistoffset */
    0,                              /* tp_iter */
    0,                              /* tp_iternext */
    Lrm_methods,                    /* tp_methods */
    Lrm_members,                    /* tp_members */
    0,                              /* tp_getset */
    0,                              /* tp_base */
    0,                              /* tp_dict */
    0,                              /* tp_descr_get */
    0,                              /* tp_descr_set */
    0,                              /* tp_dictoffset */
    (initproc)Lrm_init,             /* tp_init */
    0,                              /* tp_alloc */
    Lrm_new,                        /* tp_new */
};


#if PY_MAJOR_VERSION >= 3
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "cledadamap",                           /* m_name */
        "Shared memory read-only hash map.",    /* m_doc */
        -1,                                     /* m_size */
        Module_methods,                         /* m_methods */
        NULL,                                   /* m_reload */
        NULL,                                   /* m_traverse */
        NULL,                                   /* m_clear */
        NULL,                                   /* m_free */
    };
#endif


static PyObject *moduleinit() {
    PyObject *module;

    LrmType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&LrmType) < 0)
        return NULL;

#if PY_MAJOR_VERSION >= 3
    module = PyModule_Create(&moduledef);
#else
    module = Py_InitModule3("cledadamap", Module_methods,
        "Shared memory read-only hash map.");
#endif
    if (module == NULL)
        return NULL;

    DirtyError = PyErr_NewException("cledadamap.DirtyError", NULL, NULL);
    Py_INCREF(DirtyError);
    PyModule_AddObject(module, "DirtyError", DirtyError);

    Py_INCREF(&LrmType);
    PyModule_AddObject(module, "LedadaReadMap", (PyObject *)&LrmType);

    return module;
}


#if PY_MAJOR_VERSION < 3
    PyMODINIT_FUNC initcledadamap() {
        moduleinit();
    }
#else
    PyMODINIT_FUNC PyInit_cledadamap() {
        return moduleinit();
    }
#endif

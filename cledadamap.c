#include <sys/mman.h>
#include <fcntl.h>
#include <Python.h>
#include "structmember.h"


#define PERTURB_SHIFT	5
#define BUCKET_SIZE		4


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


static void Lrm_dealloc(LrmObject *self) {
	munmap(self->buf, self->size);
	self->ob_type->tp_free((PyObject *)self);
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
	if (self->buf == MAP_FAILED) {
		close(fd);
		PyErr_SetString(PyExc_OSError, "Can't create mmap.");
		return -1;
	}

	close(fd);

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

	name_str = PyString_AsString(name);

	mask = self->num_buckets - 1;
	long hash = PyObject_Hash(name);
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

		name_size = PyString_GET_SIZE(name);
		chunk = (Chunk *)(self->buf + bucket->chunk_pointer);

		if ((name_size == chunk->key_len) && (strncmp(&chunk->data, name_str, chunk->key_len) == 0)) {
			return PyString_FromStringAndSize(&chunk->data + chunk->key_len, chunk->value_len);
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

	return PyString_AsDecodedObject(result, "utf8", NULL);
}


static PyMemberDef Lrm_members[] = {
	{NULL}
};


static PyMethodDef Lrm_methods[] = {
	{"get", (PyCFunction)Lrm_get, METH_VARARGS, "Return value by key, otherwise None if not found"},
	{"uget", (PyCFunction)Lrm_uget, METH_VARARGS, "Return value by key (as unicode object), otherwise None if not found"},
    {NULL}
};


static PyTypeObject LrmType = {
	PyObject_HEAD_INIT(NULL)
    0,                         		/*ob_size*/
    "cledadamap.LedadaReadMap",     /*tp_name*/
    sizeof(LrmObject),         		/*tp_basicsize*/
    0,                         		/*tp_itemsize*/
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
    "ledada read-only hash map",  	/* tp_doc */
	0,		                        /* tp_traverse */
    0,		                        /* tp_clear */
    0,		                        /* tp_richcompare */
    0,		                        /* tp_weaklistoffset */
    0,		                        /* tp_iter */
    0,		                        /* tp_iternext */
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


PyMODINIT_FUNC initcledadamap() {
    PyObject *module;

    LrmType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&LrmType) < 0)
        return;

    module = Py_InitModule3("cledadamap", Lrm_methods,
    	"Shared memory read-only hash map.");
    if (module == NULL)
    	return;

    DirtyError = PyErr_NewException("cledadamap.DirtyError", NULL, NULL);
    Py_INCREF(DirtyError);
    PyModule_AddObject(module, "DirtyError", DirtyError);

    Py_INCREF(&LrmType);
    PyModule_AddObject(module, "LedadaReadMap", (PyObject *)&LrmType);
}


int main(int argc, char *argv[]) {
	Py_SetProgramName(argv[0]);
	Py_Initialize();
	initcledadamap();
}

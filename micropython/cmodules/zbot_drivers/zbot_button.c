#include "py/runtime.h"
#include "py/obj.h"
#include "py/mphal.h"
#include "py/misc.h"
#include <string.h>

typedef struct _zbot_button_obj_t {
    mp_obj_base_t base;
    mp_obj_t pin;
    mp_obj_t name;
    mp_obj_t pull;
    int button_id;
    int gpio;
    bool active_low;
    int debounce_ms;
    bool candidate_pressed;
    mp_uint_t candidate_ms;
    bool pressed;
    mp_uint_t last_change_ms;
    int press_count;
    int release_count;
    int press_latch;
    int release_latch;
} zbot_button_obj_t;

static mp_obj_t zbot_button_machine_attr(qstr attr) {
    mp_obj_t machine = mp_import_name(MP_QSTR_machine, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    return mp_load_attr(machine, attr);
}

static bool zbot_button_str_eq(mp_obj_t obj, const char *value) {
    if (!mp_obj_is_str(obj)) {
        return false;
    }
    return strcmp(mp_obj_str_get_str(obj), value) == 0;
}

static mp_obj_t zbot_button_pin_pull(mp_obj_t pin_type, mp_obj_t pull_obj, mp_obj_t default_pull) {
    mp_obj_t pull = pull_obj == mp_const_none ? default_pull : pull_obj;

    if (zbot_button_str_eq(pull, "up") || zbot_button_str_eq(pull, "pull_up") || zbot_button_str_eq(pull, "pullup")) {
        return mp_load_attr(pin_type, MP_QSTR_PULL_UP);
    }
    if (zbot_button_str_eq(pull, "down") || zbot_button_str_eq(pull, "pull_down") || zbot_button_str_eq(pull, "pulldown")) {
        return mp_load_attr(pin_type, MP_QSTR_PULL_DOWN);
    }
    if (zbot_button_str_eq(pull, "none") || zbot_button_str_eq(pull, "off") || zbot_button_str_eq(pull, "float") || zbot_button_str_eq(pull, "floating")) {
        return mp_const_none;
    }
    if (zbot_button_str_eq(default_pull, "up") || zbot_button_str_eq(default_pull, "pull_up") || zbot_button_str_eq(default_pull, "pullup")) {
        return mp_load_attr(pin_type, MP_QSTR_PULL_UP);
    }
    return mp_load_attr(pin_type, MP_QSTR_PULL_DOWN);
}

static bool zbot_button_raw_pressed(zbot_button_obj_t *self) {
    mp_obj_t dest[2];
    mp_load_method(self->pin, MP_QSTR_value, dest);
    int raw = mp_obj_get_int(mp_call_method_n_kw(0, 0, dest));
    return self->active_low ? raw == 0 : raw == 1;
}

static mp_obj_t zbot_button_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_button_id,
        ARG_gpio,
        ARG_name,
        ARG_pull,
        ARG_active_low,
        ARG_debounce_ms,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_button_id, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_gpio, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_name, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_pull, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_active_low, MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_debounce_ms, MP_ARG_INT, {.u_int = 35} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_t pin_type = zbot_button_machine_attr(MP_QSTR_Pin);
    mp_obj_t pin_in = mp_load_attr(pin_type, MP_QSTR_IN);
    mp_obj_t default_pull = MP_OBJ_NEW_QSTR(MP_QSTR_down);
    mp_obj_t pin_pull = zbot_button_pin_pull(pin_type, args[ARG_pull].u_obj, default_pull);

    mp_obj_t pin_args[3] = {
        mp_obj_new_int(args[ARG_gpio].u_int),
        pin_in,
        pin_pull,
    };
    mp_obj_t pin = pin_pull == mp_const_none
        ? mp_call_function_n_kw(pin_type, 2, 0, pin_args)
        : mp_call_function_n_kw(pin_type, 3, 0, pin_args);

    zbot_button_obj_t *self = m_new_obj(zbot_button_obj_t);
    self->base.type = type;
    self->pin = pin;
    self->button_id = args[ARG_button_id].u_int;
    self->gpio = args[ARG_gpio].u_int;
    if (args[ARG_name].u_obj == mp_const_none) {
        vstr_t name;
        vstr_init(&name, 8);
        vstr_printf(&name, "B%d", self->button_id);
        self->name = mp_obj_new_str_from_vstr(&name);
    } else {
        self->name = args[ARG_name].u_obj;
    }
    self->pull = args[ARG_pull].u_obj == mp_const_none ? default_pull : args[ARG_pull].u_obj;
    self->active_low = args[ARG_active_low].u_bool;
    self->debounce_ms = args[ARG_debounce_ms].u_int;

    mp_uint_t now = mp_hal_ticks_ms();
    bool initial = zbot_button_raw_pressed(self);
    self->candidate_pressed = initial;
    self->candidate_ms = now;
    self->pressed = initial;
    self->last_change_ms = now;
    self->press_count = 0;
    self->release_count = 0;
    self->press_latch = 0;
    self->release_latch = 0;
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t zbot_button_update(size_t n_args, const mp_obj_t *args) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_uint_t now = n_args > 1 && args[1] != mp_const_none ? (mp_uint_t)mp_obj_get_int(args[1]) : mp_hal_ticks_ms();
    bool raw_pressed = zbot_button_raw_pressed(self);

    if (raw_pressed != self->candidate_pressed) {
        self->candidate_pressed = raw_pressed;
        self->candidate_ms = now;
        return mp_const_false;
    }

    if (raw_pressed != self->pressed && (mp_int_t)(now - self->candidate_ms) >= self->debounce_ms) {
        self->pressed = raw_pressed;
        self->last_change_ms = now;

        if (self->pressed) {
            self->press_count++;
            self->press_latch++;
        } else {
            self->release_count++;
            self->release_latch++;
        }
        return mp_const_true;
    }

    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_button_update_obj, 1, 2, zbot_button_update);

static mp_obj_t zbot_button_read(mp_obj_t self_in) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->pressed);
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_button_read_obj, zbot_button_read);

static mp_obj_t zbot_button_value(mp_obj_t self_in) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->pressed ? 1 : 0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_button_value_obj, zbot_button_value);

static mp_obj_t zbot_button_released(mp_obj_t self_in) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(!self->pressed);
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_button_released_obj, zbot_button_released);

static mp_obj_t zbot_button_was_pressed(mp_obj_t self_in) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->press_latch <= 0) {
        return mp_const_false;
    }
    self->press_latch--;
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_button_was_pressed_obj, zbot_button_was_pressed);

static mp_obj_t zbot_button_was_released(mp_obj_t self_in) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->release_latch <= 0) {
        return mp_const_false;
    }
    self->release_latch--;
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_button_was_released_obj, zbot_button_was_released);

static mp_obj_t zbot_button_presses(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_reset };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_reset, MP_ARG_BOOL, {.u_bool = false} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args - 1, pos_args + 1, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_button_obj_t *self = MP_OBJ_TO_PTR(pos_args[0]);
    int count = self->press_count;
    if (args[ARG_reset].u_bool) {
        self->press_count = 0;
    }
    return mp_obj_new_int(count);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(zbot_button_presses_obj, 1, zbot_button_presses);

static mp_obj_t zbot_button_releases(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_reset };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_reset, MP_ARG_BOOL, {.u_bool = false} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args - 1, pos_args + 1, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_button_obj_t *self = MP_OBJ_TO_PTR(pos_args[0]);
    int count = self->release_count;
    if (args[ARG_reset].u_bool) {
        self->release_count = 0;
    }
    return mp_obj_new_int(count);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(zbot_button_releases_obj, 1, zbot_button_releases);

static mp_obj_t zbot_button_snapshot(mp_obj_t self_in) {
    zbot_button_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t dict = mp_obj_new_dict(11);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_id), mp_obj_new_int(self->button_id));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_name), self->name);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_gpio), mp_obj_new_int(self->gpio));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_available), mp_const_true);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_pressed), mp_obj_new_bool(self->pressed));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_value), mp_obj_new_int(self->pressed ? 1 : 0));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_presses), mp_obj_new_int(self->press_count));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_releases), mp_obj_new_int(self->release_count));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_last_change_ms), mp_obj_new_int_from_uint(self->last_change_ms));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_debounce_ms), mp_obj_new_int(self->debounce_ms));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_active_low), mp_obj_new_bool(self->active_low));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_pull), self->pull);
    return dict;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_button_snapshot_obj, zbot_button_snapshot);

static const mp_rom_map_elem_t zbot_button_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&zbot_button_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&zbot_button_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_value), MP_ROM_PTR(&zbot_button_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_pressed), MP_ROM_PTR(&zbot_button_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_released), MP_ROM_PTR(&zbot_button_released_obj) },
    { MP_ROM_QSTR(MP_QSTR_was_pressed), MP_ROM_PTR(&zbot_button_was_pressed_obj) },
    { MP_ROM_QSTR(MP_QSTR_was_released), MP_ROM_PTR(&zbot_button_was_released_obj) },
    { MP_ROM_QSTR(MP_QSTR_presses), MP_ROM_PTR(&zbot_button_presses_obj) },
    { MP_ROM_QSTR(MP_QSTR_releases), MP_ROM_PTR(&zbot_button_releases_obj) },
    { MP_ROM_QSTR(MP_QSTR_snapshot), MP_ROM_PTR(&zbot_button_snapshot_obj) },
};
static MP_DEFINE_CONST_DICT(zbot_button_locals_dict, zbot_button_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    zbot_button_type,
    MP_QSTR_DebouncedButton,
    MP_TYPE_FLAG_NONE,
    make_new, zbot_button_make_new,
    locals_dict, &zbot_button_locals_dict
);

static const mp_rom_map_elem_t zbot_button_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_button) },
    { MP_ROM_QSTR(MP_QSTR_DebouncedButton), MP_ROM_PTR(&zbot_button_type) },
};
static MP_DEFINE_CONST_DICT(zbot_button_module_globals, zbot_button_module_globals_table);

const mp_obj_module_t zbot_button_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_button_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_button, zbot_button_module);

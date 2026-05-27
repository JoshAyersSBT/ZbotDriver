#include "py/runtime.h"
#include "py/obj.h"
#include <string.h>
#include <stdio.h>

static bool user_main_call1(mp_obj_t zbot, qstr method, mp_obj_t arg, mp_obj_t *result) {
    if (zbot == mp_const_none) {
        return false;
    }

    mp_obj_t dest[3];
    mp_load_method_maybe(zbot, method, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return false;
    }

    dest[2] = arg;
    mp_obj_t value = mp_call_method_n_kw(1, 0, dest);
    if (result != NULL) {
        *result = value;
    }
    return true;
}

static void user_main_notify(mp_obj_t zbot, const char *message) {
    user_main_call1(zbot, MP_QSTR_notify, mp_obj_new_str(message, strlen(message)), NULL);
}

static void user_main_display(mp_obj_t zbot, const char *line1, const char *line2, const char *line3, const char *line4) {
    if (zbot == mp_const_none) {
        return;
    }

    mp_obj_t dest[6];
    mp_load_method_maybe(zbot, MP_QSTR_display, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return;
    }

    dest[2] = mp_obj_new_str(line1, strlen(line1));
    dest[3] = mp_obj_new_str(line2, strlen(line2));
    dest[4] = mp_obj_new_str(line3, strlen(line3));
    dest[5] = mp_obj_new_str(line4, strlen(line4));
    mp_call_method_n_kw(4, 0, dest);
}

static bool user_main_dict_get(mp_obj_t dict_in, qstr key, mp_obj_t *value) {
    if (!mp_obj_is_type(dict_in, &mp_type_dict)) {
        return false;
    }

    mp_map_t *map = mp_obj_dict_get_map(dict_in);
    mp_map_elem_t *elem = mp_map_lookup(map, MP_OBJ_NEW_QSTR(key), MP_MAP_LOOKUP);
    if (elem == NULL) {
        return false;
    }

    if (value != NULL) {
        *value = elem->value;
    }
    return true;
}

static bool user_main_dict_get_int(mp_obj_t dict_in, qstr key, int *value) {
    mp_obj_t item = mp_const_none;
    if (!user_main_dict_get(dict_in, key, &item) || item == mp_const_none) {
        return false;
    }

    if (mp_obj_is_int(item)) {
        *value = mp_obj_get_int(item);
        return true;
    }
    return false;
}

static bool user_main_read_rgb(mp_obj_t zbot, int port, int *r, int *g, int *b, int *clear) {
    mp_obj_t value = mp_const_none;
    if (!user_main_call1(zbot, MP_QSTR_rgb, mp_obj_new_int(port), &value) || !mp_obj_is_type(value, &mp_type_dict)) {
        return false;
    }

    int rr = 0;
    int gg = 0;
    int bb = 0;
    int cc = 0;
    bool ok = user_main_dict_get_int(value, MP_QSTR_r, &rr)
        && user_main_dict_get_int(value, MP_QSTR_g, &gg)
        && user_main_dict_get_int(value, MP_QSTR_b, &bb);
    user_main_dict_get_int(value, MP_QSTR_clear, &cc);
    if (!ok) {
        return false;
    }

    *r = rr;
    *g = gg;
    *b = bb;
    *clear = cc;
    return true;
}

static bool user_main_read_color(mp_obj_t zbot, int port, char *buf, size_t buf_len) {
    mp_obj_t value = mp_const_none;
    if (buf_len == 0 || !user_main_call1(zbot, MP_QSTR_color, mp_obj_new_int(port), &value) || value == mp_const_none) {
        return false;
    }

    if (mp_obj_is_str(value)) {
        size_t len = 0;
        const char *text = mp_obj_str_get_data(value, &len);
        if (len >= buf_len) {
            len = buf_len - 1;
        }
        memcpy(buf, text, len);
        buf[len] = '\0';
        return true;
    }
    return false;
}

static bool user_main_read_tof(mp_obj_t zbot, int port, int *distance_mm) {
    mp_obj_t value = mp_const_none;
    if (!user_main_call1(zbot, MP_QSTR_tof, mp_obj_new_int(port), &value) || value == mp_const_none) {
        return false;
    }

    if (mp_obj_is_int(value)) {
        *distance_mm = mp_obj_get_int(value);
        return true;
    }
    return false;
}

static mp_obj_t user_main_main(size_t n_args, const mp_obj_t *args) {
    mp_obj_t zbot = n_args > 0 ? args[0] : mp_const_none;

    user_main_notify(zbot, "C_USER start display sensors");
    user_main_display(zbot, "C User Main", "Color P1 wait", "ToF P2 wait", "Sensors live");
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(user_main_main_obj, 0, 1, user_main_main);

static mp_obj_t user_main_tick(size_t n_args, const mp_obj_t *args) {
    mp_obj_t zbot = n_args > 0 ? args[0] : mp_const_none;
    static uint tick_count = 0;
    tick_count++;

    char color[24] = "wait";
    char line2[32];
    char line3[32];
    char line4[32];
    int r = 0;
    int g = 0;
    int b = 0;
    int clear = 0;
    int tof = 0;

    bool color_ok = user_main_read_color(zbot, 1, color, sizeof(color));
    bool rgb_ok = user_main_read_rgb(zbot, 1, &r, &g, &b, &clear);
    bool tof_ok = user_main_read_tof(zbot, 2, &tof);

    if (color_ok) {
        snprintf(line2, sizeof(line2), "P1 color %s", color);
    } else {
        snprintf(line2, sizeof(line2), "P1 color wait");
    }

    if (rgb_ok) {
        snprintf(line3, sizeof(line3), "RGB %d %d %d", r, g, b);
    } else {
        snprintf(line3, sizeof(line3), "RGB wait");
    }

    if (tof_ok) {
        snprintf(line4, sizeof(line4), "P2 ToF %dmm", tof);
    } else {
        snprintf(line4, sizeof(line4), "P2 ToF wait");
    }

    if ((tick_count % 4) == 0 && rgb_ok) {
        snprintf(line2, sizeof(line2), "P1 clear %d", clear);
        snprintf(line3, sizeof(line3), "Color %s", color_ok ? color : "wait");
    }

    user_main_display(zbot, "C User Sensors", line2, line3, line4);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(user_main_tick_obj, 0, 1, user_main_tick);

static const mp_rom_map_elem_t user_main_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_user_main) },
    { MP_ROM_QSTR(MP_QSTR_USER_MAIN_KIND), MP_ROM_QSTR(MP_QSTR_c) },
    { MP_ROM_QSTR(MP_QSTR_USER_MAIN_TICK_MS), MP_ROM_INT(1000) },
    { MP_ROM_QSTR(MP_QSTR_main), MP_ROM_PTR(&user_main_main_obj) },
    { MP_ROM_QSTR(MP_QSTR_tick), MP_ROM_PTR(&user_main_tick_obj) },
};
static MP_DEFINE_CONST_DICT(user_main_module_globals, user_main_module_globals_table);

const mp_obj_module_t user_main_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&user_main_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_user_main, user_main_module);

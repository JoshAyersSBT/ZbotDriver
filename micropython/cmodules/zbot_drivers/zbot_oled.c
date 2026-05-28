#include "py/runtime.h"
#include "py/obj.h"

typedef struct _zbot_sh1106_obj_t {
    mp_obj_base_t base;
    mp_obj_t i2c;
    mp_obj_t buffer;
    mp_obj_t framebuffer;
    uint8_t addr;
    int width;
    int height;
    int pages;
    int column_offset;
    bool external_vcc;
} zbot_sh1106_obj_t;

static void zbot_sh1106_write_cmd(zbot_sh1106_obj_t *self, uint8_t cmd) {
    uint8_t data[2] = { 0x80, cmd };
    mp_obj_t dest[4];
    mp_load_method(self->i2c, MP_QSTR_writeto, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = mp_obj_new_bytes(data, 2);
    mp_call_method_n_kw(2, 0, dest);
}

static void zbot_sh1106_write_data(zbot_sh1106_obj_t *self, const uint8_t *buf, size_t len) {
    uint8_t *data = m_new(uint8_t, len + 1);
    data[0] = 0x40;
    for (size_t i = 0; i < len; i++) {
        data[i + 1] = buf[i];
    }

    mp_obj_t dest[4];
    mp_load_method(self->i2c, MP_QSTR_writeto, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = mp_obj_new_bytes(data, len + 1);
    mp_call_method_n_kw(2, 0, dest);
    m_del(uint8_t, data, len + 1);
}

static void zbot_sh1106_init_display(zbot_sh1106_obj_t *self) {
    static const uint8_t cmds[] = {
        0xae,
        0xd5, 0x80,
        0xa8, 0x3f,
        0xd3, 0x00,
        0x40,
        0xad, 0x8b,
        0xa1,
        0xc8,
        0xda, 0x12,
        0x81, 0x7f,
        0xd9, 0x22,
        0xdb, 0x35,
        0xa4,
        0xa6,
        0xaf,
    };

    for (size_t i = 0; i < MP_ARRAY_SIZE(cmds); i++) {
        zbot_sh1106_write_cmd(self, cmds[i]);
    }
}

static void zbot_sh1106_fb_call(zbot_sh1106_obj_t *self, qstr method, size_t n_args, mp_obj_t *args) {
    mp_obj_t dest[6];
    mp_load_method(self->framebuffer, method, dest);
    for (size_t i = 0; i < n_args; i++) {
        dest[2 + i] = args[i];
    }
    mp_call_method_n_kw(n_args, 0, dest);
}

static mp_obj_t zbot_sh1106_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_width,
        ARG_height,
        ARG_i2c,
        ARG_addr,
        ARG_external_vcc,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_width, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 128} },
        { MP_QSTR_height, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 64} },
        { MP_QSTR_i2c, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_addr, MP_ARG_INT, {.u_int = 0x3c} },
        { MP_QSTR_external_vcc, MP_ARG_BOOL, {.u_bool = false} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_sh1106_obj_t *self = m_new_obj(zbot_sh1106_obj_t);
    self->base.type = type;
    self->width = args[ARG_width].u_int;
    self->height = args[ARG_height].u_int;
    self->pages = self->height / 8;
    self->addr = args[ARG_addr].u_int & 0x7f;
    self->i2c = args[ARG_i2c].u_obj;
    self->external_vcc = args[ARG_external_vcc].u_bool;
    self->column_offset = 2;

    size_t buf_len = self->width * self->pages;
    self->buffer = mp_obj_new_bytearray(buf_len, NULL);

    mp_obj_t framebuf = mp_import_name(MP_QSTR_framebuf, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t framebuffer_type = mp_load_attr(framebuf, MP_QSTR_FrameBuffer);
    mp_obj_t mono_vlsb = mp_load_attr(framebuf, MP_QSTR_MONO_VLSB);
    mp_obj_t fb_args[4] = {
        self->buffer,
        mp_obj_new_int(self->width),
        mp_obj_new_int(self->height),
        mono_vlsb,
    };
    self->framebuffer = mp_call_function_n_kw(framebuffer_type, 4, 0, fb_args);

    zbot_sh1106_init_display(self);

    mp_obj_t fill_args[1] = { mp_obj_new_int(0) };
    zbot_sh1106_fb_call(self, MP_QSTR_fill, 1, fill_args);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t zbot_sh1106_fill(mp_obj_t self_in, mp_obj_t color_in) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t args[1] = { color_in };
    zbot_sh1106_fb_call(self, MP_QSTR_fill, 1, args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_sh1106_fill_obj, zbot_sh1106_fill);

static mp_obj_t zbot_sh1106_text(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[4] = {
        args[1],
        args[2],
        args[3],
        n_args > 4 ? args[4] : mp_obj_new_int(1),
    };
    zbot_sh1106_fb_call(self, MP_QSTR_text, 4, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_text_obj, 4, 5, zbot_sh1106_text);

static mp_obj_t zbot_sh1106_pixel(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[3] = {
        args[1],
        args[2],
        n_args > 3 ? args[3] : mp_obj_new_int(1),
    };
    zbot_sh1106_fb_call(self, MP_QSTR_pixel, 3, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_pixel_obj, 3, 4, zbot_sh1106_pixel);

static mp_obj_t zbot_sh1106_hline(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[4] = { args[1], args[2], args[3], args[4] };
    zbot_sh1106_fb_call(self, MP_QSTR_hline, 4, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_hline_obj, 5, 5, zbot_sh1106_hline);

static mp_obj_t zbot_sh1106_vline(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[4] = { args[1], args[2], args[3], args[4] };
    zbot_sh1106_fb_call(self, MP_QSTR_vline, 4, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_vline_obj, 5, 5, zbot_sh1106_vline);

static mp_obj_t zbot_sh1106_line(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[5] = { args[1], args[2], args[3], args[4], args[5] };
    zbot_sh1106_fb_call(self, MP_QSTR_line, 5, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_line_obj, 6, 6, zbot_sh1106_line);

static mp_obj_t zbot_sh1106_rect(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[5] = {
        args[1],
        args[2],
        args[3],
        args[4],
        n_args > 5 ? args[5] : mp_obj_new_int(1),
    };
    zbot_sh1106_fb_call(self, MP_QSTR_rect, 5, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_rect_obj, 5, 6, zbot_sh1106_rect);

static mp_obj_t zbot_sh1106_fill_rect(size_t n_args, const mp_obj_t *args) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t fb_args[5] = { args[1], args[2], args[3], args[4], args[5] };
    zbot_sh1106_fb_call(self, MP_QSTR_fill_rect, 5, fb_args);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_sh1106_fill_rect_obj, 6, 6, zbot_sh1106_fill_rect);

static mp_obj_t zbot_sh1106_show(mp_obj_t self_in) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(self->buffer, &bufinfo, MP_BUFFER_READ);
    const uint8_t *buf = (const uint8_t *)bufinfo.buf;

    for (int page = 0; page < self->pages; page++) {
        zbot_sh1106_write_cmd(self, 0xb0 | page);
        zbot_sh1106_write_cmd(self, self->column_offset & 0x0f);
        zbot_sh1106_write_cmd(self, 0x10 | (self->column_offset >> 4));
        zbot_sh1106_write_data(self, buf + (self->width * page), self->width);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_sh1106_show_obj, zbot_sh1106_show);

static mp_obj_t zbot_sh1106_write_cmd_obj(mp_obj_t self_in, mp_obj_t cmd_in) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(self_in);
    zbot_sh1106_write_cmd(self, mp_obj_get_int(cmd_in) & 0xff);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_sh1106_write_cmd_obj_obj, zbot_sh1106_write_cmd_obj);

static mp_obj_t zbot_sh1106_poweroff(mp_obj_t self_in) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(self_in);
    zbot_sh1106_write_cmd(self, 0xae);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_sh1106_poweroff_obj, zbot_sh1106_poweroff);

static mp_obj_t zbot_sh1106_contrast(mp_obj_t self_in, mp_obj_t contrast_in) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(self_in);
    zbot_sh1106_write_cmd(self, 0x81);
    zbot_sh1106_write_cmd(self, mp_obj_get_int(contrast_in) & 0xff);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_sh1106_contrast_obj, zbot_sh1106_contrast);

static mp_obj_t zbot_sh1106_invert(mp_obj_t self_in, mp_obj_t invert_in) {
    zbot_sh1106_obj_t *self = MP_OBJ_TO_PTR(self_in);
    zbot_sh1106_write_cmd(self, mp_obj_is_true(invert_in) ? 0xa7 : 0xa6);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_sh1106_invert_obj, zbot_sh1106_invert);

static const mp_rom_map_elem_t zbot_sh1106_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&zbot_sh1106_fill_obj) },
    { MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&zbot_sh1106_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_pixel), MP_ROM_PTR(&zbot_sh1106_pixel_obj) },
    { MP_ROM_QSTR(MP_QSTR_hline), MP_ROM_PTR(&zbot_sh1106_hline_obj) },
    { MP_ROM_QSTR(MP_QSTR_vline), MP_ROM_PTR(&zbot_sh1106_vline_obj) },
    { MP_ROM_QSTR(MP_QSTR_line), MP_ROM_PTR(&zbot_sh1106_line_obj) },
    { MP_ROM_QSTR(MP_QSTR_rect), MP_ROM_PTR(&zbot_sh1106_rect_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill_rect), MP_ROM_PTR(&zbot_sh1106_fill_rect_obj) },
    { MP_ROM_QSTR(MP_QSTR_show), MP_ROM_PTR(&zbot_sh1106_show_obj) },
    { MP_ROM_QSTR(MP_QSTR_write_cmd), MP_ROM_PTR(&zbot_sh1106_write_cmd_obj_obj) },
    { MP_ROM_QSTR(MP_QSTR_poweroff), MP_ROM_PTR(&zbot_sh1106_poweroff_obj) },
    { MP_ROM_QSTR(MP_QSTR_contrast), MP_ROM_PTR(&zbot_sh1106_contrast_obj) },
    { MP_ROM_QSTR(MP_QSTR_invert), MP_ROM_PTR(&zbot_sh1106_invert_obj) },
};
static MP_DEFINE_CONST_DICT(zbot_sh1106_locals_dict, zbot_sh1106_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    zbot_sh1106_type,
    MP_QSTR_SH1106_I2C,
    MP_TYPE_FLAG_NONE,
    make_new, zbot_sh1106_make_new,
    locals_dict, &zbot_sh1106_locals_dict
);

static const mp_rom_map_elem_t zbot_oled_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_oled) },
    { MP_ROM_QSTR(MP_QSTR_SH1106_I2C), MP_ROM_PTR(&zbot_sh1106_type) },
};
static MP_DEFINE_CONST_DICT(zbot_oled_module_globals, zbot_oled_module_globals_table);

const mp_obj_module_t zbot_oled_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_oled_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_oled, zbot_oled_module);

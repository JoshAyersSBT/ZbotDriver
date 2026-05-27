#include "py/runtime.h"
#include "py/obj.h"
#include "py/mphal.h"

#define MPU6050_REG_PWR_MGMT_1 (0x6b)
#define MPU6050_REG_SMPLRT_DIV (0x19)
#define MPU6050_REG_CONFIG (0x1a)
#define MPU6050_REG_GYRO_CONFIG (0x1b)
#define MPU6050_REG_ACCEL_CONFIG (0x1c)
#define MPU6050_REG_ACCEL_XOUT_H (0x3b)

typedef struct _zbot_mpu6050_obj_t {
    mp_obj_base_t base;
    mp_obj_t i2c;
    mp_obj_t mux;
    mp_obj_t mux_channel;
    uint8_t addr;
} zbot_mpu6050_obj_t;

static mp_obj_t zbot_mpu_machine_attr(qstr attr) {
    mp_obj_t machine = mp_import_name(MP_QSTR_machine, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    return mp_load_attr(machine, attr);
}

static void zbot_mpu_select(zbot_mpu6050_obj_t *self) {
    if (self->mux != mp_const_none && self->mux_channel != mp_const_none) {
        mp_obj_t dest[3];
        mp_load_method(self->mux, MP_QSTR_select, dest);
        dest[2] = self->mux_channel;
        mp_call_method_n_kw(1, 0, dest);
    }
}

static void zbot_mpu_write8(zbot_mpu6050_obj_t *self, uint8_t reg, uint8_t value) {
    zbot_mpu_select(self);
    uint8_t data[1] = { value };
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_writeto_mem, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_bytes(data, 1);
    mp_call_method_n_kw(3, 0, dest);
}

static mp_obj_t zbot_mpu_read_mem(zbot_mpu6050_obj_t *self, uint8_t reg, size_t len) {
    zbot_mpu_select(self);
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_readfrom_mem, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_int(len);
    return mp_call_method_n_kw(3, 0, dest);
}

static int16_t zbot_i16_be(const uint8_t *data) {
    return (int16_t)((data[0] << 8) | data[1]);
}

static mp_obj_t zbot_mpu6050_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_i2c_id,
        ARG_sda_gpio,
        ARG_scl_gpio,
        ARG_freq,
        ARG_addr,
        ARG_mux,
        ARG_mux_channel,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_i2c_id, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_sda_gpio, MP_ARG_INT, {.u_int = 21} },
        { MP_QSTR_scl_gpio, MP_ARG_INT, {.u_int = 22} },
        { MP_QSTR_freq, MP_ARG_INT, {.u_int = 400000} },
        { MP_QSTR_addr, MP_ARG_INT, {.u_int = 0x68} },
        { MP_QSTR_mux, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_mux_channel, MP_ARG_OBJ, {.u_obj = mp_const_none} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_t i2c_type = zbot_mpu_machine_attr(MP_QSTR_I2C);
    mp_obj_t pin_type = zbot_mpu_machine_attr(MP_QSTR_Pin);
    mp_obj_t sda_pin = mp_call_function_1(pin_type, mp_obj_new_int(args[ARG_sda_gpio].u_int));
    mp_obj_t scl_pin = mp_call_function_1(pin_type, mp_obj_new_int(args[ARG_scl_gpio].u_int));
    mp_obj_t i2c_args[7] = {
        mp_obj_new_int(args[ARG_i2c_id].u_int),
        MP_OBJ_NEW_QSTR(MP_QSTR_sda),
        sda_pin,
        MP_OBJ_NEW_QSTR(MP_QSTR_scl),
        scl_pin,
        MP_OBJ_NEW_QSTR(MP_QSTR_freq),
        mp_obj_new_int(args[ARG_freq].u_int),
    };
    mp_obj_t i2c = mp_call_function_n_kw(i2c_type, 1, 3, i2c_args);

    zbot_mpu6050_obj_t *self = m_new_obj(zbot_mpu6050_obj_t);
    self->base.type = type;
    self->i2c = i2c;
    self->addr = args[ARG_addr].u_int & 0x7f;
    self->mux = args[ARG_mux].u_obj;
    self->mux_channel = args[ARG_mux_channel].u_obj;

    zbot_mpu_write8(self, MPU6050_REG_PWR_MGMT_1, 0x00);
    mp_hal_delay_ms(100);
    zbot_mpu_write8(self, MPU6050_REG_SMPLRT_DIV, 9);
    zbot_mpu_write8(self, MPU6050_REG_CONFIG, 0x03);
    zbot_mpu_write8(self, MPU6050_REG_GYRO_CONFIG, 0x00);
    zbot_mpu_write8(self, MPU6050_REG_ACCEL_CONFIG, 0x00);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t zbot_mpu6050_read_raw(mp_obj_t self_in) {
    zbot_mpu6050_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return zbot_mpu_read_mem(self, MPU6050_REG_ACCEL_XOUT_H, 14);
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_mpu6050_read_raw_obj, zbot_mpu6050_read_raw);

static mp_obj_t zbot_mpu6050_read_scaled(mp_obj_t self_in) {
    zbot_mpu6050_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t raw = zbot_mpu_read_mem(self, MPU6050_REG_ACCEL_XOUT_H, 14);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(raw, &bufinfo, MP_BUFFER_READ);
    const uint8_t *data = (const uint8_t *)bufinfo.buf;

    int16_t ax = zbot_i16_be(data + 0);
    int16_t ay = zbot_i16_be(data + 2);
    int16_t az = zbot_i16_be(data + 4);
    int16_t temp_raw = zbot_i16_be(data + 6);
    int16_t gx = zbot_i16_be(data + 8);
    int16_t gy = zbot_i16_be(data + 10);
    int16_t gz = zbot_i16_be(data + 12);

    mp_obj_t dict = mp_obj_new_dict(7);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_ax_g), mp_obj_new_float((mp_float_t)ax / 16384.0f));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_ay_g), mp_obj_new_float((mp_float_t)ay / 16384.0f));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_az_g), mp_obj_new_float((mp_float_t)az / 16384.0f));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_gx_dps), mp_obj_new_float((mp_float_t)gx / 131.0f));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_gy_dps), mp_obj_new_float((mp_float_t)gy / 131.0f));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_gz_dps), mp_obj_new_float((mp_float_t)gz / 131.0f));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_temp_c), mp_obj_new_float(((mp_float_t)temp_raw / 340.0f) + 36.53f));
    return dict;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_mpu6050_read_scaled_obj, zbot_mpu6050_read_scaled);

static const mp_rom_map_elem_t zbot_mpu6050_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_read_raw), MP_ROM_PTR(&zbot_mpu6050_read_raw_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_scaled), MP_ROM_PTR(&zbot_mpu6050_read_scaled_obj) },
};
static MP_DEFINE_CONST_DICT(zbot_mpu6050_locals_dict, zbot_mpu6050_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    zbot_mpu6050_type,
    MP_QSTR_MPU6050,
    MP_TYPE_FLAG_NONE,
    make_new, zbot_mpu6050_make_new,
    locals_dict, &zbot_mpu6050_locals_dict
);

static const mp_rom_map_elem_t zbot_mpu6050_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_mpu6050) },
    { MP_ROM_QSTR(MP_QSTR_MPU6050), MP_ROM_PTR(&zbot_mpu6050_type) },
};
static MP_DEFINE_CONST_DICT(zbot_mpu6050_module_globals, zbot_mpu6050_module_globals_table);

const mp_obj_module_t zbot_mpu6050_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_mpu6050_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_mpu6050, zbot_mpu6050_module);

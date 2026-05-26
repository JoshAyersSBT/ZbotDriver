#include "py/runtime.h"
#include "py/obj.h"

typedef struct _zbot_servo_obj_t {
    mp_obj_base_t base;
    mp_obj_t pwm;
    int freq_hz;
    int min_us;
    int max_us;
} zbot_servo_obj_t;

STATIC mp_obj_t zbot_servo_machine_attr(qstr attr) {
    mp_obj_t machine = mp_import_name(MP_QSTR_machine, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    return mp_load_attr(machine, attr);
}

STATIC int zbot_servo_clamp_int(int value, int lo, int hi) {
    if (value < lo) {
        return lo;
    }
    if (value > hi) {
        return hi;
    }
    return value;
}

STATIC mp_obj_t zbot_servo_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_gpio,
        ARG_freq_hz,
        ARG_min_us,
        ARG_max_us,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_gpio, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_freq_hz, MP_ARG_INT, {.u_int = 50} },
        { MP_QSTR_min_us, MP_ARG_INT, {.u_int = 500} },
        { MP_QSTR_max_us, MP_ARG_INT, {.u_int = 2500} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_t pin_type = zbot_servo_machine_attr(MP_QSTR_Pin);
    mp_obj_t pwm_type = zbot_servo_machine_attr(MP_QSTR_PWM);
    mp_obj_t pin_out = mp_load_attr(pin_type, MP_QSTR_OUT);

    mp_obj_t pin_args[2] = {
        mp_obj_new_int(args[ARG_gpio].u_int),
        pin_out,
    };
    mp_obj_t pin = mp_call_function_n_kw(pin_type, 2, 0, pin_args);
    mp_obj_t pwm = mp_call_function_1(pwm_type, pin);

    mp_obj_t freq_dest[3];
    mp_load_method(pwm, MP_QSTR_freq, freq_dest);
    freq_dest[2] = mp_obj_new_int(args[ARG_freq_hz].u_int);
    mp_call_method_n_kw(1, 0, freq_dest);

    zbot_servo_obj_t *self = m_new_obj(zbot_servo_obj_t);
    self->base.type = type;
    self->pwm = pwm;
    self->freq_hz = args[ARG_freq_hz].u_int;
    self->min_us = args[ARG_min_us].u_int;
    self->max_us = args[ARG_max_us].u_int;
    return MP_OBJ_FROM_PTR(self);
}

STATIC void zbot_servo_write_duty(zbot_servo_obj_t *self, int duty_u16, int duty_10bit) {
    mp_obj_t dest[3];
    mp_load_method_maybe(self->pwm, MP_QSTR_duty_u16, dest);
    if (dest[0] != MP_OBJ_NULL) {
        dest[2] = mp_obj_new_int(duty_u16);
        mp_call_method_n_kw(1, 0, dest);
        return;
    }

    mp_load_method(self->pwm, MP_QSTR_duty, dest);
    dest[2] = mp_obj_new_int(duty_10bit);
    mp_call_method_n_kw(1, 0, dest);
}

STATIC mp_obj_t zbot_servo_angle(mp_obj_t self_in, mp_obj_t deg_in) {
    zbot_servo_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int angle = zbot_servo_clamp_int(mp_obj_get_int(deg_in), 0, 180);
    int pulse = self->min_us + ((self->max_us - self->min_us) * angle) / 180;
    int period_us = 1000000 / self->freq_hz;
    int duty_u16 = (pulse * 65535) / period_us;
    int duty_10bit = (pulse * 1023) / period_us;

    zbot_servo_write_duty(self, duty_u16, duty_10bit);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(zbot_servo_angle_obj, zbot_servo_angle);

STATIC mp_obj_t zbot_servo_deinit(mp_obj_t self_in) {
    zbot_servo_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t dest[2];
    mp_load_method(self->pwm, MP_QSTR_deinit, dest);
    mp_call_method_n_kw(0, 0, dest);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_servo_deinit_obj, zbot_servo_deinit);

STATIC const mp_rom_map_elem_t zbot_servo_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_angle), MP_ROM_PTR(&zbot_servo_angle_obj) },
    { MP_ROM_QSTR(MP_QSTR_write_angle), MP_ROM_PTR(&zbot_servo_angle_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&zbot_servo_deinit_obj) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_servo_locals_dict, zbot_servo_locals_dict_table);

STATIC const mp_obj_type_t zbot_servo_type = {
    { &mp_type_type },
    .name = MP_QSTR_Servo,
    .make_new = zbot_servo_make_new,
    .locals_dict = (mp_obj_dict_t *)&zbot_servo_locals_dict,
};

STATIC const mp_rom_map_elem_t zbot_servo_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_servo) },
    { MP_ROM_QSTR(MP_QSTR_Servo), MP_ROM_PTR(&zbot_servo_type) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_servo_module_globals, zbot_servo_module_globals_table);

const mp_obj_module_t zbot_servo_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_servo_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_servo, zbot_servo_module);

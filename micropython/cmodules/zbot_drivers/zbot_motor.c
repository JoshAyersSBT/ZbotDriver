#include "py/runtime.h"
#include "py/obj.h"

typedef struct _zbot_motor_obj_t {
    mp_obj_base_t base;
    mp_obj_t dir;
    mp_obj_t pwm;
    bool invert_pwm;
    int power;
} zbot_motor_obj_t;

static mp_obj_t zbot_machine_attr(qstr attr) {
    mp_obj_t machine = mp_import_name(MP_QSTR_machine, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    return mp_load_attr(machine, attr);
}

static int zbot_clamp_int(int value, int lo, int hi) {
    if (value < lo) {
        return lo;
    }
    if (value > hi) {
        return hi;
    }
    return value;
}

static void zbot_motor_write_duty(zbot_motor_obj_t *self, int duty_u16) {
    duty_u16 = zbot_clamp_int(duty_u16, 0, 65535);
    if (self->invert_pwm) {
        duty_u16 = 65535 - duty_u16;
    }

    mp_obj_t dest[3];
    mp_load_method(self->pwm, MP_QSTR_duty_u16, dest);
    dest[2] = mp_obj_new_int(duty_u16);
    mp_call_method_n_kw(1, 0, dest);
}

static mp_obj_t zbot_motor_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_pwm_gpio,
        ARG_dir_gpio,
        ARG_pwm_freq_hz,
        ARG_invert_pwm,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_pwm_gpio, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_dir_gpio, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_pwm_freq_hz, MP_ARG_INT, {.u_int = 20000} },
        { MP_QSTR_invert_pwm, MP_ARG_BOOL, {.u_bool = false} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_t pin_type = zbot_machine_attr(MP_QSTR_Pin);
    mp_obj_t pwm_type = zbot_machine_attr(MP_QSTR_PWM);
    mp_obj_t pin_out = mp_load_attr(pin_type, MP_QSTR_OUT);

    mp_obj_t dir_args[2] = {
        mp_obj_new_int(args[ARG_dir_gpio].u_int),
        pin_out,
    };
    mp_obj_t dir = mp_call_function_n_kw(pin_type, 2, 0, dir_args);

    mp_obj_t pwm_pin_args[2] = {
        mp_obj_new_int(args[ARG_pwm_gpio].u_int),
        pin_out,
    };
    mp_obj_t pwm_pin = mp_call_function_n_kw(pin_type, 2, 0, pwm_pin_args);

    mp_obj_t pwm_args[3] = {
        pwm_pin,
        MP_OBJ_NEW_QSTR(MP_QSTR_freq),
        mp_obj_new_int(args[ARG_pwm_freq_hz].u_int),
    };
    mp_obj_t pwm = mp_call_function_n_kw(pwm_type, 1, 1, pwm_args);

    zbot_motor_obj_t *self = m_new_obj(zbot_motor_obj_t);
    self->base.type = type;
    self->dir = dir;
    self->pwm = pwm;
    self->invert_pwm = args[ARG_invert_pwm].u_bool;
    self->power = 0;
    zbot_motor_write_duty(self, 0);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t zbot_motor_set(mp_obj_t self_in, mp_obj_t forward_in, mp_obj_t duty_in) {
    zbot_motor_obj_t *self = MP_OBJ_TO_PTR(self_in);
    bool forward = mp_obj_is_true(forward_in);
    int duty_u16 = mp_obj_get_int(duty_in);

    mp_obj_t dir_dest[3];
    mp_load_method(self->dir, MP_QSTR_value, dir_dest);
    dir_dest[2] = mp_obj_new_int(forward ? 1 : 0);
    mp_call_method_n_kw(1, 0, dir_dest);

    zbot_motor_write_duty(self, duty_u16);
    int percent = (zbot_clamp_int(duty_u16, 0, 65535) * 100) / 65535;
    self->power = forward ? percent : -percent;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(zbot_motor_set_obj, zbot_motor_set);

static mp_obj_t zbot_motor_set_power(mp_obj_t self_in, mp_obj_t power_in) {
    int power = zbot_clamp_int(mp_obj_get_int(power_in), -100, 100);
    if (power == 0) {
        zbot_motor_obj_t *self = MP_OBJ_TO_PTR(self_in);
        self->power = 0;
        zbot_motor_write_duty(self, 0);
        return mp_const_none;
    }
    int duty_u16 = ((power < 0 ? -power : power) * 65535) / 100;
    return zbot_motor_set(self_in, mp_obj_new_bool(power > 0), mp_obj_new_int(duty_u16));
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_motor_set_power_obj, zbot_motor_set_power);

static mp_obj_t zbot_motor_stop(mp_obj_t self_in) {
    zbot_motor_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->power = 0;
    zbot_motor_write_duty(self, 0);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_motor_stop_obj, zbot_motor_stop);

static mp_obj_t zbot_motor_power(mp_obj_t self_in) {
    zbot_motor_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->power);
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_motor_power_obj, zbot_motor_power);

static mp_obj_t zbot_motor_deinit(mp_obj_t self_in) {
    zbot_motor_obj_t *self = MP_OBJ_TO_PTR(self_in);
    zbot_motor_stop(self_in);
    mp_obj_t dest[2];
    mp_load_method(self->pwm, MP_QSTR_deinit, dest);
    mp_call_method_n_kw(0, 0, dest);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_motor_deinit_obj, zbot_motor_deinit);

static const mp_rom_map_elem_t zbot_motor_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&zbot_motor_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_power), MP_ROM_PTR(&zbot_motor_set_power_obj) },
    { MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&zbot_motor_stop_obj) },
    { MP_ROM_QSTR(MP_QSTR_brake), MP_ROM_PTR(&zbot_motor_stop_obj) },
    { MP_ROM_QSTR(MP_QSTR_power), MP_ROM_PTR(&zbot_motor_power_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&zbot_motor_deinit_obj) },
};
static MP_DEFINE_CONST_DICT(zbot_motor_locals_dict, zbot_motor_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    zbot_motor_type,
    MP_QSTR_Motor,
    MP_TYPE_FLAG_NONE,
    make_new, zbot_motor_make_new,
    locals_dict, &zbot_motor_locals_dict
);

static const mp_rom_map_elem_t zbot_motor_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_motor) },
    { MP_ROM_QSTR(MP_QSTR_Motor), MP_ROM_PTR(&zbot_motor_type) },
};
static MP_DEFINE_CONST_DICT(zbot_motor_module_globals, zbot_motor_module_globals_table);

const mp_obj_module_t zbot_motor_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_motor_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_motor, zbot_motor_module);

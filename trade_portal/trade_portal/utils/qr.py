import qrcode
from io import BytesIO
# from PIL import Image


def get_qrcode_image(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image()
    sio = BytesIO()
    img.save(sio)
    sio.seek(0)
    return sio.read()
    # pil_image = Image.open(sio)
    # return pil_image

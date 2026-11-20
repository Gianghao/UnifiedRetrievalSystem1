"""Synthetic Vietnamese chat corpus + queries for the retrieval benchmark (stdlib only).

Replaces strategies_bench.build(). All names, companies, codes are invented.

Corpus mix (target proportions, per chunk):
  ~19%  short replies with little context ("ok", "dạ", "uk", "=))", "tks"...)
  ~76%  one-line chat messages from ~190 slot templates: work logistics (meeting,
        file, invoice, contract, deadline, shipping), food/coffee, traffic/rain,
        family, money, travel, shopping, jokes. Of these:
          ~40% teencode tokens (ko, đc, j, z, r, nx, bh, ns, ib, đt, mn, ae ...)
          ~35% typed without diacritics (không dấu)
          ~25% code-switch / mostly English ("deadline", "confirm", "pls send me ...")
          plus elongation (okkk), typos, particles (nha, á, ạ), emoji.
  ~5%   long chunks of ~300 words (contract/PDF page or meeting transcript).
Planted (about 165 chunks, every size >= 1000): one gold chunk per query, written
with reserved rare names/brands/codes that filler never uses (see FACTS / __main__).
Query types: exact_code, paraphrase, long_chunk_fact, no_diacritics, code_switch,
teencode, vague_context, correction (old + later correction), unanswerable.
Final order is shuffled, but each stale chunk is forced to sit before its correction.
"""
import random
import re
import time
import unicodedata
from collections import Counter

# ---------- no-diacritics ----------
_VN = ("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
       "ùúủũụưừứửữựỳýỷỹỵ")
_TBL = {ord(c): unicodedata.normalize("NFD", c)[0] for c in _VN + _VN.upper()}
_TBL[ord("đ")] = "d"
_TBL[ord("Đ")] = "D"


def nd(s):
    return s.translate(_TBL)


_HAS_DIAC = re.compile("[" + _VN + _VN.upper() + "đĐ]")

# ---------- filler banks ----------
SHORT = ["ok", "oke a", "dạ", "uk", "ừ", "để mai nha", "chốt vậy đi", "haha", "=))", ":))",
         "ok e", "thanks a", "tks", "r", "rep sau nha", "ok ạ", "vâng ạ", "được á", "ờ", "ừm",
         "hihi", "kk", "ok nha", "đc", "dạ vâng", "cảm ơn nha", "thanks", "oki", "okie", "ừa",
         "ờ ha", "ủa", "hả", "?", "sao z", "thật hả", "trời", "hay quá", "tuyệt", "chuẩn",
         "đúng r", "ko sao", "thôi kệ", "đợi tí", "1 lát nha", "đang đi", "tới r", "ra liền",
         "ok chốt", "oke e", "dạ e biết r ạ", "👍", "😂", "😅", "❤️", "🙏", "ờ để a xem",
         "xíu nha", "ok luôn", "ừ đc", "mai tính", "tính sau", "thôi ok", "k sao đâu", "ok", "dạ",
         "uk", "ừ", "ok a", "dạ ok ạ", "haha ok", "hehe", "z hả", "vậy hả", "ờ ok", "rồi nha",
         "nhé", "ok bạn", "okela", "sure", "noted", "got it", "ok thanks", "đã nhận", "dạ em nhận r ạ"]

BANK = {
    "name": ["Minh", "Hùng", "Lan", "Tuấn", "Hà", "Linh", "Nam", "Trang", "Dũng", "Huy", "Thảo",
             "Phong", "Mai", "Long", "Quân", "Vy", "Hạnh", "Đạt", "Ngọc", "Sơn", "Bình", "Khánh",
             "Yến", "Thành", "Tâm", "Hiếu", "Phương", "Thư", "Kiên", "Oanh", "Jimmy", "Tony"],
    "pron": ["a", "c", "e", "anh", "chị", "bạn", "ông", "cô", "sếp", "anh", "chị"],
    "pn": ["ổng", "bả", "ảnh", "chị ấy", "nó", "sếp", "thằng đó", "bà đó", "chế"],
    "thing": ["file", "báo cáo", "hợp đồng", "slide", "hóa đơn", "bản thiết kế", "bảng giá",
              "biên bản", "đề xuất", "timeline", "proposal", "report", "invoice", "bản demo", "form",
              "checklist", "báo giá", "đơn hàng", "phụ lục", "bảng lương"],
    "time": ["3h chiều", "14:30", "9h sáng", "5h", "8h tối", "10h30", "trước 12h", "sau 4h", "7h45",
             "lúc 2h", "11:00", "16:15", "6h chiều", "8h"],
    "day": ["mai", "hnay", "thứ 6", "t2", "t4", "tuần sau", "cuối tuần", "chiều nay", "sáng mai",
            "tối nay", "hôm qua", "thứ 7", "chủ nhật", "mốt", "thứ 5", "đầu tuần", "cuối tháng"],
    "food": ["cơm tấm", "bún bò", "phở", "bánh mì", "trà sữa", "cơm gà", "lẩu", "bún chả", "mì cay",
             "cháo", "hủ tiếu", "pizza", "gà rán", "bánh xèo", "cơm văn phòng", "bún đậu"],
    "drink": ["cà phê sữa", "trà đào", "bạc xỉu", "trà sữa", "nước cam", "cà phê muối", "matcha",
              "sinh tố bơ", "trà tắc", "cacao đá"],
    "place": ["Vũng Tàu", "Đà Lạt", "Nha Trang", "Phú Quốc", "Sapa", "Huế", "Đà Nẵng", "Cần Thơ",
              "Quy Nhơn", "Hà Nội", "Sài Gòn", "Phan Thiết"],
    "road": ["cầu Sài Gòn", "Nguyễn Huệ", "Phạm Văn Đồng", "quốc lộ 1", "vòng xoay Điện Biên Phủ",
             "ngã tư Hàng Xanh", "Cộng Hòa", "Xa lộ Hà Nội", "Võ Văn Kiệt", "Nguyễn Văn Linh"],
    "shop": ["Shopee", "Lazada", "Tiki", "Grab", "Tiktok shop", "Highlands", "Circle K", "Winmart"],
    "family": ["mẹ", "ba", "bà ngoại", "em gái", "chị hai", "con bé", "ông nội", "dì", "cậu", "má"],
    "item": ["áo khoác", "giày", "tai nghe", "ốp lưng", "balo", "đồng hồ", "máy xay", "nồi chiên",
             "quạt", "bàn phím", "sạc dự phòng", "chuột", "ô", "áo mưa"],
    "weather": ["mưa", "mưa to", "nắng gắt", "kẹt xe", "ngập", "nóng", "lạnh"],
    "big": ["1,2 tỷ", "2 tỷ 5", "850tr", "3,4 tỷ", "1 tỷ 8", "4,5 tỷ"],
    "eng": ["deadline", "meeting", "feedback", "report", "update", "plan", "task", "approve",
            "confirm", "review"],
}
PREF = ["INV", "HD", "PO", "BB", "DH"]
RESERVED = set()  # planted codes/passwords filler must never generate


def g_date(r):
    return f"{r.randint(1, 28)}/{r.randint(1, 12)}"


def g_code(r):
    while True:
        c = f"{PREF[r.randrange(5)]}-{r.randint(2023, 2026)}-{r.randint(1, 9999):04d}"
        if c not in RESERVED:
            return c


def g_amt(r):
    x = r.random()
    if x < .35:
        return f"{r.randrange(50, 1000, 50)}k"
    if x < .6:
        return f"{r.randint(1, 40)}tr{r.randint(1, 9)}"
    if x < .8:
        return f"{r.randint(1, 99)}tr"
    if x < .9:
        return f"{r.randint(1, 3)},{r.randint(1, 9)} tỷ"
    return f"{r.randrange(20, 500, 5)}.000đ"


def g_who(r):
    return BANK["pron"][r.randrange(11)] + " " + BANK["name"][r.randrange(32)]


GEN = {"date": g_date, "code": g_code, "amt": g_amt, "who": g_who,
       "pct": lambda r: r.randint(10, 95), "n2": lambda r: r.randint(5, 60)}


class _F(dict):
    r = None

    def __missing__(self, k):
        b = BANK.get(k)
        return b[int(self.r.random() * len(b))] if b else GEN[k](self.r)


TOPIC = [
    # work logistics
    "mai {time} họp nha, nhớ mang {thing}", "{who} ơi, {thing} gửi chưa v",
    "e gửi {thing} r nha a, a check giúp e", "check giùm e cái {thing} {code} với",
    "{who} nói {thing} {code} cần sửa lại",
    "deadline {thing} là {day} nha mn, ai chưa xong thì rep", "meeting {day} dời qua {time} nha",
    "sếp hỏi {thing} {code} r đó, update gấp đi", "ok e, a check r confirm lại sau nhé",
    "pls send me the {thing} b4 {time}", "feedback của khách về {thing} sao r e",
    "anh share cái {thing} lên drive giúp e nha", "{thing} này cần approve trước {day} ạ",
    "em note lại r, {day} em gửi", "book phòng họp {time} giúp a nha",
    "cancel meeting {day} đi, sếp bận", "team mình OT {day} ko mn?",
    "hôm nay KPI tháng này chốt chưa mn", "onboard bạn mới {day}, ai join ko",
    "call nhanh 5p đc ko a, e có cái này cần confirm", "inbox a cái {thing} r, a xem nha",
    "cái {thing} {code} a đã ký r, e lấy bản gốc nha", "đơn {code} giao {day} nha, khách bảo ok r",
    "{code} thanh toán {amt} r, kế toán check giúp e", "hóa đơn {code} bị sai thuế, e xuất lại nha",
    "khách sale vừa confirm đơn {code}, tổng {amt}", "PO {code} chưa approve, ai chase giúp e",
    "hợp đồng {code} gửi {who} ký chưa", "nhớ nộp {thing} {day} nhé, trễ là bị nhắc đó",
    "{who} ơi cho e xin lại cái {thing} hôm bữa với", "task này {who} làm hay em làm v",
    "đang fix bug, chắc {time} xong", "report tuần này em gửi sếp r, ko biết sếp duyệt chưa",
    "e update plan r, a xem rồi cho ý kiến nha", "hnay ai trực kho z",
    "mai {who} nghỉ phép, việc gấp thì gọi {who} nha", "kho báo hàng về {day} nha, ai nhận",
    "đơn ship {code} đang ở {place}, mai tới", "shipper gọi 3 lần r mà ko ai nghe máy",
    "gửi hàng đi {place} mất 3 ngày nha", "mn ơi {thing} mới nhất ở đâu z",
    "slide này dài quá, cắt bớt đi a", "file bị lỗi font, e gửi lại bản pdf nha",
    "deadline sát nút mà sếp đổi yêu cầu nữa =))", "cuối tuần OT nữa hả, trời",
    "nhớ tắt máy lạnh trc khi về nha mn", "pass wifi phòng họp là j z, quên r",
    "chìa khóa kho ai giữ z mn", "khách hẹn {day} lúc {time}, ai đi cùng em",
    "đợt này report Q3 trễ mấy ngày r, sếp nhắc hoài", "ai có số sdt bên kho ko, e cần gọi gấp",
    "anh gửi lại {thing} {code} giúp em, mail em ko nhận đc", "xuất {thing} {code} nhưng thiếu mã số thuế",
    "hôm qua họp xong có note lại ko mn", "{who} approve giúp e cái {thing} đi, gấp á",
    "bản {thing} v2 e để trong folder chung nha", "kéo e vào group mới với, e chưa thấy",
    "mới nhận hàng, đủ rồi nha, tks", "đối soát tháng này lệch {amt}, ai check lại giúp",
    "got it, will update u asap", "thanks, noted. will review {day}", "sorry i'm late, traffic is crazy",
    "can u check the invoice {code} pls", "let's sync {day} {time}", "meeting moved to {day}, pls confirm",
    "just sent u the file, pls check", "ok will do, thanks", "pls approve the {thing} today",
    "any update on {code}?", "ok e, a join call lúc {time} nha, share link giúp a",
    # food / coffee
    "trưa nay ăn {food} ko", "đi uống {drink} hem", "{drink} ly lớn nha, ít đường",
    "đặt {food} giúp a 2 phần nha", "quán {food} đầu hẻm đóng cửa r",
    "e mua {drink} cho mn r nha, tới nhận nè", "hnay ăn j z mn", "đói quá, ăn {food} đi",
    "{food} ở đây ngon á, mai đi lại đi", "ăn {food} mà quên mang tiền, ck lại nha",
    "cafe {time} nha, a ra sớm xíu", "tối nay nhậu ko ae", "ai ăn {food} ko, e đặt chung",
    "quán {drink} mới mở gần cty ngon lắm nha",
    # traffic / rain
    "đang kẹt xe ở {road}, tới trễ xíu nha", "mưa quá trời, ai có áo mưa ko",
    "{road} ngập r, đi đường khác đi", "trời {weather} z, mai chắc nghỉ",
    "vừa ra khỏi nhà, 15p nữa tới", "grab đang tới, chờ xíu nha", "xe hết xăng giữa đường, trời ơi",
    "hnay đi làm sớm kẻo kẹt", "đường {road} đang sửa, né ra nha", "kẹt xe ở {road} từ sáng tới giờ luôn",
    # family
    "{family} bảo cuối tuần về ăn cơm", "{family} bệnh nên mai e xin nghỉ nha",
    "tối nay đón {family} ở sân bay lúc {time}", "nhà có đám giỗ {day}, e về quê nha",
    "{family} gọi hoài, để e gọi lại", "con bé nay có buổi họp phụ huynh",
    "đưa {family} đi khám, chắc trễ xíu", "{family} nấu {food} ngon lắm, qua ăn đi",
    # money
    "ck cho a {amt} r nha, check giúp e", "a chuyển khoản {amt} r đó e",
    "tiền nhà tháng này {amt}, ai chưa ck thì ck nha", "chia tiền ăn mỗi người {amt} nha",
    "ck nhầm r, trả lại giùm e {amt} nha", "lương về chưa mn", "nay ví e hết tiền, cho mượn {amt} đc ko",
    "trả a {amt} hôm bữa nha", "giá này {amt} hơi mắc á", "cọc {amt} giữ chỗ nha",
    "tổng cộng {amt}, chưa tính ship", "tiền thưởng tết năm nay {amt} á, vui quá",
    "căn đó giá {big} luôn á", "bên kia báo giá {big}, mắc quá", "e ck {amt} r, a check nha",
    # travel
    "cuối tuần đi {place} ko, rủ ae đi", "book vé đi {place} {day} nha, {time} bay",
    "khách sạn ở {place} 2 đêm {amt}", "đi {place} về đen thui luôn =))",
    "nhớ mang giấy tờ khi đi {place} nha", "chuyến bay trễ 2 tiếng, chán quá",
    "tour {place} 3 ngày 2 đêm giá {amt}", "ai đi {place} {day} cho e đi ké với",
    # shopping
    "đặt {item} trên {shop} r, {day} tới", "cái {item} này giảm giá còn {amt} nè",
    "mua {item} chưa, a thấy đang sale á", "hàng {shop} giao nhầm {item} r, đổi trả sao đây",
    "e muốn mua {item} mà phân vân quá", "cái {item} này xài ổn ko mn", "sale 11/11 mua gì đây",
    "mn ơi ai biết chỗ sửa {item} ko",
    # jokes / chat
    "haha trời ơi cười muốn xỉu", "mày bị điên hả =))", "tao nói r mà mày ko nghe",
    "ủa sao z, hôm qua còn ok mà", "bồ ơi hnay đi chơi ko", "ổng nói z thiệt hả",
    "bả giận r đó, lo xin lỗi đi", "chế ơi giúp em cái này với", "nay sếp vui ghê, chắc có chuyện gì hay",
    "ngủ chưa ae, 2h sáng r", "thôi đi ngủ đây, mai dậy sớm",
    "ai ở nhà ko, giao hàng mà ko ai nhận", "hôm nay thứ mấy v, nhầm hoài", "trời lạnh quá ae ơi",
    "chúc mừng sinh nhật {name} nha 🎂", "{name} ơi nhớ mang {item} cho tao nha",
    "mày đi chưa, tao đợi nãy giờ", "mệt quá, hnay làm cả ngày", "thức khuya quá, mắt thâm luôn r",
    "hen, mai gặp nha", "ê nay có phim hay nè, đi ko", "bà ơi cho tui mượn cái sạc",
    "nhớ mày quá, cuối tuần đi chơi nha", "{name} nói {name} bị cảm, ai có thuốc ko",
    "đi chơi ko, tao bao {drink}", "ổng ns j z, e ko hiểu", "tao mới thấy {name} ở {road} á",
    "ê {name}, sao mày ko rep tin nhắn z", "cười đau bụng luôn, xem clip này đi 😂",
]

TEEN = {"không": "ko", "được": "đc", "gì": "j", "vậy": "z", "rồi": "r", "nữa": "nx", "nói": "ns",
        "với": "vs", "trước": "trc", "điện thoại": "đt", "mọi": "m", "biết": "bt", "bạn": "bn",
        "anh": "a", "em": "e", "chị": "c", "hôm": "hôm", "mình": "mk", "làm": "lm", "người": "ng",
        "thôi": "thui", "nhiều": "nhiu", "okay": "oke", "bây": "bây", "nhắn": "ib", "tin": "tin",
        "khi": "khi", "thế": "z", "sao": "s", "gửi": "gửi", "cũng": "cx", "nhưng": "nhưng",
        "ngày": "ngày", "mai": "mai", "dạ": "dạ"}
PARTICLES = [" nha", " nhé", " á", " ạ", " đó", " luôn", " hen", " nè", " ha", " đi", " ơi"]
EMOJI = ["😂", "👍", "😅", "🙏", "=))", ":))", "haha", "😭", "❤️", "hihi", "😆", "🥲"]

CONTRACT = [
    "Điều {pct}. Bên A có trách nhiệm thanh toán cho Bên B toàn bộ giá trị hợp đồng số {code} theo đúng tiến độ đã thỏa thuận trong phụ lục kèm theo.",
    "Bên B cam kết cung cấp hàng hóa đúng chủng loại, số lượng và chất lượng như đã ghi trong đơn đặt hàng, kèm theo đầy đủ chứng từ hợp lệ.",
    "Trong trường hợp chậm thanh toán quá {n2} ngày kể từ ngày đến hạn, Bên A phải chịu lãi phạt theo mức lãi suất quy định tại điều khoản này.",
    "Hai bên đồng ý rằng mọi thay đổi, bổ sung đối với hợp đồng chỉ có hiệu lực khi được lập thành văn bản và có chữ ký của người đại diện hợp pháp.",
    "Thời hạn giao hàng được tính từ ngày Bên B nhận được khoản tạm ứng đầu tiên và không quá {n2} ngày làm việc.",
    "Mỗi bên có nghĩa vụ giữ bí mật toàn bộ thông tin kinh doanh, kỹ thuật và tài chính mà bên kia cung cấp trong quá trình thực hiện hợp đồng.",
    "Bên B chịu trách nhiệm bảo hành sản phẩm trong thời hạn {n2} tháng kể từ ngày bàn giao, trừ các hư hỏng do lỗi sử dụng của Bên A.",
    "Việc nghiệm thu được thực hiện tại kho của Bên A với sự tham gia của đại diện hai bên và được lập thành biên bản có xác nhận.",
    "Giá trị hợp đồng chưa bao gồm thuế giá trị gia tăng, thuế này sẽ được thể hiện trên hóa đơn theo quy định pháp luật hiện hành.",
    "Nếu một bên đơn phương chấm dứt hợp đồng mà không có lý do chính đáng thì phải bồi thường {pct}% giá trị phần hợp đồng chưa thực hiện.",
    "Các thông báo giữa hai bên phải được gửi bằng văn bản qua đường bưu điện hoặc thư điện tử đến địa chỉ đã đăng ký trong hợp đồng.",
    "Trường hợp bất khả kháng bao gồm thiên tai, dịch bệnh, chiến tranh hoặc quyết định của cơ quan nhà nước làm ảnh hưởng trực tiếp đến việc thực hiện hợp đồng.",
    "Bên A có quyền kiểm tra chất lượng hàng hóa trong vòng {n2} ngày kể từ ngày nhận và thông báo bằng văn bản nếu phát hiện sai sót.",
    "Báo cáo tài chính quý được lập theo mẫu thống nhất, gồm bảng cân đối kế toán, báo cáo kết quả kinh doanh và thuyết minh kèm theo.",
    "Tổng doanh thu của quý tăng {pct}% so với cùng kỳ năm trước, chủ yếu nhờ các đơn hàng từ khách hàng doanh nghiệp.",
    "Chi phí vận chuyển và lưu kho được phân bổ theo tỷ lệ sản lượng thực tế của từng đơn hàng trong kỳ báo cáo.",
    "Phụ lục này là một phần không tách rời của hợp đồng và có hiệu lực kể từ ngày {date} cho đến khi hai bên có thỏa thuận khác.",
    "Mọi tranh chấp phát sinh trước hết được giải quyết thông qua thương lượng; nếu không thành sẽ đưa ra Tòa án có thẩm quyền để giải quyết.",
    "Bên B phải mua bảo hiểm cho hàng hóa trong suốt quá trình vận chuyển và cung cấp bản sao giấy chứng nhận bảo hiểm cho Bên A.",
    "Số lượng nhân sự tham gia dự án được duy trì ở mức {n2} người, trong đó có {n2} kỹ sư chịu trách nhiệm trực tiếp về kỹ thuật.",
    "Kế hoạch thanh toán được chia thành ba đợt, đợt một thanh toán {pct}% giá trị hợp đồng ngay sau khi hai bên ký kết.",
    "Bên A xác nhận đã đọc, hiểu rõ và đồng ý với toàn bộ các điều khoản nêu trên và không có bất kỳ khiếu nại nào về nội dung hợp đồng.",
    "Hợp đồng được lập thành hai bản có giá trị pháp lý như nhau, mỗi bên giữ một bản để thực hiện kể từ ngày ký.",
    "Rủi ro mất mát hoặc hư hỏng hàng hóa được chuyển từ Bên B sang Bên A tại thời điểm hàng hóa được giao cho đơn vị vận chuyển.",
    "Khoản phạt vi phạm tối đa không vượt quá {pct}% giá trị phần nghĩa vụ bị vi phạm theo quy định của pháp luật.",
    "Danh mục tài liệu kèm theo gồm bảng báo giá, bản vẽ kỹ thuật, biên bản làm việc ngày {date} và giấy ủy quyền của người đại diện.",
]
TRANSCRIPT = [
    "Trong cuộc họp, anh {name} nói rằng tiến độ của dự án hiện đã hoàn thành khoảng {pct}% so với kế hoạch ban đầu.",
    "Chị {name} đề nghị bộ phận kinh doanh cập nhật lại danh sách khách hàng trước ngày {date} để kịp báo cáo lên ban giám đốc.",
    "Sau khi thảo luận, mọi người thống nhất sẽ tổ chức buổi đánh giá lại vào {day} và mời thêm đại diện phòng kế toán tham dự.",
    "Anh {name} cho biết nhà cung cấp hiện đang chậm giao khoảng {n2} ngày và đề xuất tìm thêm một nguồn hàng dự phòng.",
    "Chị {name} hỏi về chi phí phát sinh, và phòng tài chính trả lời rằng khoản này sẽ được xem xét trong kỳ ngân sách tới.",
    "Cuối buổi họp, {name} tổng kết các việc cần làm gồm hoàn thiện báo cáo, gửi báo giá cho khách và đặt lịch họp tuần sau.",
    "Trong phần trao đổi, anh {name} lo ngại rằng nếu không tăng thêm nhân sự thì kế hoạch giao hàng cuối tháng sẽ bị ảnh hưởng.",
    "Mọi người đồng ý rằng khách hàng đang quan tâm nhiều nhất đến thời gian giao hàng chứ không phải mức giá.",
    "Chị {name} nhắc lại rằng báo cáo doanh số phải được nộp trước {time} của {day} để phòng kế hoạch tổng hợp.",
    "Theo anh {name}, hệ thống cũ thường xuyên bị chậm vào giờ cao điểm nên cần được nâng cấp trong quý này.",
    "Bộ phận chăm sóc khách hàng báo cáo đã nhận được {n2} khiếu nại trong tuần, phần lớn liên quan đến việc giao hàng chậm.",
    "Anh {name} đề xuất thành lập một nhóm nhỏ gồm ba người để theo dõi riêng các đơn hàng có giá trị lớn.",
    "Sau khi nghe ý kiến từ các phòng ban, giám đốc yêu cầu mỗi trưởng nhóm gửi kế hoạch chi tiết trước ngày {date}.",
    "Chị {name} cho rằng việc thay đổi nhà cung cấp trong thời điểm này là rủi ro vì hợp đồng hiện tại còn hiệu lực đến {date}.",
    "Cuộc họp kết thúc lúc {time}, biên bản sẽ được {name} gửi qua email cho tất cả người tham dự trong ngày.",
    "Anh {name} báo cáo rằng ngân sách tháng này đã sử dụng khoảng {pct}% và còn lại đủ để chi trả cho các hoạt động cần thiết.",
    "Mọi người thảo luận về việc chuyển sang làm việc linh hoạt, trong đó chị {name} ủng hộ và anh {name} muốn thử nghiệm trước.",
    "Phòng kỹ thuật xác nhận lỗi đã được khắc phục, tuy nhiên vẫn cần thêm {n2} ngày để kiểm thử trước khi triển khai chính thức.",
    "Chị {name} thông báo công ty sẽ tổ chức buổi đào tạo nội bộ vào {day}, tất cả nhân viên mới bắt buộc phải tham gia.",
    "Anh {name} nhấn mạnh rằng chất lượng sản phẩm quan trọng hơn tốc độ và không nên rút ngắn thời gian kiểm tra.",
    "Về vấn đề chi phí quảng cáo, nhóm marketing đề nghị giữ nguyên ngân sách và tập trung vào các kênh đã mang lại hiệu quả.",
    "Sau cuộc gọi với khách hàng, {name} cho biết họ đồng ý gia hạn thêm {n2} ngày nhưng yêu cầu có cam kết bằng văn bản.",
    "Anh {name} đưa ra số liệu cho thấy tỷ lệ khách hàng quay lại đã tăng lên {pct}% sau khi cải thiện chính sách đổi trả.",
    "Cuối cùng, ban lãnh đạo thống nhất phương án hai, giao chị {name} theo dõi tiến độ và báo cáo hằng tuần vào sáng {day}.",
]


def _long(r, f, bank, extra=None):
    out, words = [], 0
    while words < 295:
        s = bank[int(r.random() * len(bank))].format_map(f)
        out.append(s)
        words += s.count(" ") + 1
    return out


def long_chunk(r, f, fact=None):
    bank = CONTRACT if r.random() < .5 else TRANSCRIPT
    ss = _long(r, f, bank)
    if fact:
        ss.insert(len(ss) // 2, fact)
    return " ".join(ss)


def short_reply(r):
    s = SHORT[int(r.random() * len(SHORT))]
    x = r.random()
    if x < .12 and s[-1].isalpha():
        s += s[-1] * r.randint(1, 3)
    elif x < .24:
        s += " " + EMOJI[int(r.random() * 12)]
    return s


LEAD = ["ê", "ủa", "à mà", "mà", "nè", "ơi", "btw", "thôi", "chốt nha:", "mn ơi", "ok,", "vậy là", "tiện thể",
        "nói chung", "à quên,", "sorry,", "hnay", "này,", "khoan,", "à"]
TAIL = ["gấp á", "giúp e với", "nhớ nha", "được ko", "nhé mn", "tks nhiều", "{day} nha", "trước {time} nha",
        "ai biết ko", "để a lo", "e lo cho", "rep giúp e", "{who} biết đó", "xong báo e", "lỡ quên thì nhắc nha",
        "hơi gấp á", "chắc vậy", "ko biết nữa", "cho e xin ý kiến", "khỏi lo", "nhắc {who} giùm", "nhé {name}",
        "{amt} thôi", "lúc {time} nha", "ở {road} á", "tính sao đây", "để tính", "trời ơi"]


def topic_msg(r, f):
    t = TOPIC[int(r.random() * len(TOPIC))].format_map(f)
    x = r.random()
    if x < .4:
        t = LEAD[int(r.random() * 20)] + " " + t
    x = r.random()
    if x < .45:
        t += ", " + TAIL[int(r.random() * 28)].format_map(f)
    x = r.random()
    if x < .4:  # teencode
        t = " ".join([TEEN.get(w, w) for w in t.split(" ")])
    if r.random() < .3 and t[-1].isalnum():
        t += PARTICLES[int(r.random() * 11)]
    if r.random() < .06:  # elongation
        w = t.split(" ")
        i = r.randrange(len(w))
        if w[i] and w[i][-1].isalpha():
            w[i] += w[i][-1] * r.randint(2, 4)
        t = " ".join(w)
    if r.random() < .05 and len(t) > 12:  # typo: drop a char
        i = r.randrange(1, len(t) - 1)
        t = t[:i] + t[i + 1:]
    if r.random() < .13:
        t += " " + EMOJI[int(r.random() * 12)]
    if r.random() < .12:
        t = t[0].upper() + t[1:]
    if r.random() < .33:  # không dấu
        t = nd(t)
    return t


# ---------- planted items ----------
NAME_GIVEN = ["Hùng", "Tuấn", "Lan", "Minh", "Hà", "Linh", "Nam", "Trang", "Dũng", "Huy", "Thảo",
              "Phong", "Mai", "Long", "Quân", "Vy", "Hạnh", "Đạt", "Ngọc", "Sơn", "Bình", "Khánh",
              "Yến", "Thành", "Tâm", "Hiếu", "Phương", "Thư", "Kiên", "Oanh", "Chi", "Vân", "Tú",
              "Nhi", "Duy", "Giang", "Hải", "Loan", "Phúc", "Thịnh"]
NAME_SUFFIX = ["Béo", "Còi", "Cận", "Râu", "Mập", "Nâu", "Xù", "Ngố", "Sến", "Lùn", "Đen", "Gầy"]
BRANDS = ["Sen Vàng", "Trăng Non", "Mây Tre", "Cá Chép Đỏ", "Hải Đăng Xanh", "Lúa Mới", "Bồ Câu Trắng",
          "Đèn Lồng", "Cỏ Ba Lá", "Mận Hậu", "Sao Mai Bắc", "Phượng Tím", "Gió Đồng", "Trầm Hương",
          "Nắng Sớm", "Bình Minh Đỏ", "Thạch Sanh", "Cúc Họa Mi", "Hạt Dẻ", "Quế Lâm", "Sóc Nâu",
          "Dâu Tằm", "Đại Ngàn", "Cánh Buồm", "Ngọc Lan Tây", "Tràm Chim", "Rạng Đông Mới",
          "Cầu Vồng", "Lục Bình", "Bạch Dương", "Suối Tiên", "Mía Đường", "Hổ Phách", "Tre Xanh",
          "Vạn Xuân", "Thiên Lý", "Bông Gòn", "Lá Diêu Bông", "Nhạn Trắng", "Sơn Ca", "Dừa Xiêm",
          "Hồng Hạc", "Rồng Xanh", "Lửa Hồng", "Đồi Chè", "Bãi Sậy", "Hoàng Yến", "Chuồn Chuồn",
          "Thiên Nga Đen", "Cỏ May", "Vỏ Quýt", "Mắm Tôm", "Chim Cú", "Hạc Giấy", "Gò Nổi",
          "Cây Đa", "Bến Nứa", "Sương Mai", "Mật Ong Rừng", "Nấm Hương", "Ốc Gạo", "Kê Vàng"]
BR_A = ["Kim", "Ngân", "Bạch", "Thanh", "Thạch", "Tử", "Lam", "Xích", "Huyền", "Thiết"]
BR_B = ["Tước", "Long", "Phụng", "Lân", "Quy", "Ưng", "Báo", "Sư", "Điểu", "Mãng"]
PWWORDS = ["Hoasen", "Camau", "Baoloc", "Songhong", "Truongson", "Maihoa", "Cuclac", "Thanhtra"]


class _P(dict):
    """lazy planted slots: P1/P2 names, B1/B2 brands, C/C1 codes, PW/PW2 passwords, N ext numbers"""
    def __init__(self, ctx):
        self.ctx = ctx

    def __missing__(self, k):
        v = self.ctx[k.rstrip("0123456789")]()
        self[k] = v
        return v


WARMUP = [("chìa khóa xe tải {B1} anh {P1} đang giữ", "ai giữ chìa khóa xe tải {B1}", "{B1}"),
          ("tối nay {P1} đãi cả nhóm ăn ở quán {B1} nha", "tối nay {P1} đãi ăn ở đâu", "{P1}"),
          ("hóa đơn {C} đã thanh toán đủ 18tr5 r nha", "hóa đơn {C} đã thanh toán chưa", "{C}")]

EXACT = [
    ("a {P1} đang giữ bản gốc {C} nha, ai cần thì hỏi ảnh", "{C} ai giữ v", "{C}"),
    ("{C} bị sai số tiền, kế toán {P1} đang sửa lại", "check giùm {C}", "{C}"),
    ("e gửi {C} cho {B1} r nha, họ confirm nhận rồi", "{C} gửi chưa", "{C}"),
    ("đơn {C} giao trễ 2 ngày do kho {B1} hết hàng", "tại sao {C} bị trễ", "{C}"),
    ("{C} chốt giá 45tr, a {P1} đã ký r", "{C} bao nhiêu tiền", "{C}"),
    ("hợp đồng {C} hết hạn 31/12, nhớ gia hạn nha", "{C} hết hạn khi nào", "{C}"),
    ("PO {C} đã approve, chờ {P1} xuất kho", "{C} approve chưa", "{C}"),
    ("ai nhận {C} chưa? e thấy {P1} ký nhận hôm qua", "ai ký nhận {C}", "{C}"),
    ("{C} thanh toán đợt 2 vào thứ 5, tổng 128tr", "{C} thanh toán đợt mấy", "{C}"),
]
PARAPHRASE = [
    ("{P1} bị sốt nên xin nghỉ", "sao hnay {P1} vắng mặt", "{P1}"),
    ("tiệc sinh nhật {P1} dời qua chủ nhật nha mn", "party của {P1} giờ tổ chức ngày nào z", "{P1}"),
    ("e đặt bàn nhà hàng {B1} lúc 7h tối thứ 7, 8 người", "mấy giờ đi ăn ở {B1} vậy", "{B1}"),
    ("xe của {P1} bị thủng lốp giữa đường nên tới trễ", "tại sao {P1} đến muộn", "{P1}"),
    ("{P1} mới chuyển tiền cọc 5tr cho chủ nhà {B1}", "ai đã trả tiền đặt cọc nhà {B1}", "{B1}"),
    ("sếp bảo tuần sau cả team làm việc remote, trừ {P1}", "tuần tới ai phải vào văn phòng, có phải {P1} ko", "{P1}"),
    ("quán {B1} đóng cửa vĩnh viễn rồi, mình đổi sang chỗ khác nha", "quán {B1} còn mở cửa ko", "{B1}"),
    ("{P1} dặn là đừng mang laptop, phòng họp có sẵn máy chiếu rồi", "{P1} nói cần chuẩn bị thiết bị gì cho buổi họp", "{P1}"),
    ("vé máy bay đi {B1} bị hủy do bão, hãng hoàn tiền trong 7 ngày", "chuyến bay {B1} sao rồi, có lấy lại tiền ko", "{B1}"),
    ("{P1} thi đậu bằng lái xe rồi, đãi cả nhóm trà sữa", "{P1} có tin vui gì ko", "{P1}"),
    ("mẹ {P1} nhập viện hôm qua, bs nói chỉ cần theo dõi thêm 2 ngày", "người nhà {P1} ốm hả, bao giờ xuất viện", "{P1}"),
    ("căn hộ {B1} giá thuê 12tr một tháng, chưa tính phí quản lý", "thuê chung cư {B1} hết bao nhiêu", "{B1}"),
    ("{P1} quên mang chìa khóa nên đứng ngoài cửa gần 1 tiếng", "{P1} bị kẹt ngoài nhà hả", "{P1}"),
    ("app {B1} cập nhật bản mới, đăng nhập phải dùng lại OTP", "sau khi update {B1} thì login thế nào", "{B1}"),
    ("hôm nay {P1} mời cả team cà phê vì được tăng lương", "{P1} đãi gì z", "{P1}"),
    ("máy lạnh phòng {B1} chảy nước, bảo vệ đã gọi thợ", "điều hòa phòng {B1} bị trục trặc gì", "{B1}"),
]
LONGFACT = [
    ("Theo thông báo, kho {B1} sẽ tạm đóng cửa ngày 14/12 để kiểm kê hàng tồn.", "khi nào kho {B1} đóng cửa kiểm kê", "{B1}"),
    ("Mức phạt chậm thanh toán đối với hợp đồng {C} được ấn định ở mức 0,05% mỗi ngày.", "phạt trễ hạn thanh toán {C} là bao nhiêu", "{C}"),
    ("Anh {P1} cho biết ngân sách quảng cáo quý 4 của {B1} được duyệt ở mức 380 triệu đồng.", "ngân sách quảng cáo {B1} quý 4 duyệt bao nhiêu", "{B1}"),
    ("Bên B cam kết bảo hành thiết bị {B1} trong thời hạn 18 tháng kể từ ngày nghiệm thu.", "bảo hành thiết bị {B1} mấy tháng", "{B1}"),
    ("Chị {P1} thông báo buổi đào tạo {B1} sẽ diễn ra tại phòng 502 vào lúc 8h30 sáng thứ Tư.", "đào tạo {B1} ở phòng nào", "{B1}"),
    ("Người đại diện nhận hàng của đợt giao {C} là ông {P1}, số CCCD đã được đăng ký trước.", "ai là người nhận hàng đợt {C}", "{C}"),
    ("Cuộc họp thống nhất dời ngày ra mắt sản phẩm {B1} sang 9/3 do chậm tiến độ kiểm thử.", "ra mắt sản phẩm {B1} dời sang ngày nào", "{B1}"),
    ("Anh {P1} đề xuất đổi nhà cung cấp bao bì sang công ty {B1} vì giá rẻ hơn 12%.", "ai đề xuất đổi bao bì sang {B1}", "{B1}"),
    ("Phí vận chuyển đơn {C} đã bao gồm bảo hiểm hàng hóa tối đa 200 triệu đồng.", "bảo hiểm hàng của {C} tối đa bao nhiêu", "{C}"),
    ("Chị {P1} sẽ chịu trách nhiệm liên hệ khách hàng {B1} và báo cáo kết quả trước thứ Sáu.", "ai phụ trách liên hệ khách {B1}", "{B1}"),
    ("Theo biên bản, tòa nhà {B1} sẽ ngừng cấp điện từ 22h đến 5h sáng ngày 3/11 để bảo trì.", "tòa {B1} cúp điện lúc nào", "{B1}"),
    ("Thời hạn nộp hồ sơ dự thầu gói {B1} là 17h ngày 28/02, hồ sơ nộp muộn không được chấp nhận.", "hạn nộp hồ sơ thầu gói {B1}", "{B1}"),
    ("Anh {P1} xác nhận máy chủ {B1} sẽ được nâng cấp RAM lên 128GB trong tháng này.", "server {B1} nâng cấp RAM bao nhiêu", "{B1}"),
    ("Công ty {B1} đồng ý giảm giá 7% nếu đơn hàng đầu tiên đạt trên 500 triệu đồng.", "{B1} giảm giá bao nhiêu phần trăm", "{B1}"),
    ("Điều 9: Mọi tranh chấp liên quan đến hợp đồng {C} được giải quyết tại Tòa án nhân dân quận 3.", "tranh chấp hợp đồng {C} giải quyết ở đâu", "{C}"),
    ("Chị {P1} nhắc rằng chương trình tri ân khách hàng {B1} kết thúc vào ngày 15/12 và không gia hạn.", "chương trình tri ân {B1} kết thúc khi nào", "{B1}"),
]
# (gold, query, fact, which side to strip: "q" query, "g" gold)
NODIAC = [
    ("Mật khẩu wifi phòng họp {B1} là {PW}", "mật khẩu wifi phòng họp {B1} là gì", "{PW}", "q"),
    ("Địa chỉ giao hàng mới của {P1} là số 45 đường {B1}, quận Tân Bình", "địa chỉ giao hàng mới của {P1} ở đâu", "{P1}", "q"),
    ("Số tài khoản công ty {B1} là {N}{N1}, ngân hàng ACB", "số tài khoản công ty {B1} là gì", "{N}{N1}", "q"),
    ("Lịch bảo trì thang máy tòa {B1} là sáng thứ Bảy tuần này", "khi nào bảo trì thang máy tòa {B1}", "{B1}", "q"),
    ("Chìa khóa tủ hồ sơ {B1} để ở bàn chị {P1}", "chìa khóa tủ hồ sơ {B1} ở đâu", "{B1}", "q"),
    ("Cô {P1} dạy tiếng Anh lớp tối thứ 3 và thứ 5 ở trung tâm {B1}", "lớp tiếng Anh trung tâm {B1} học ngày nào", "{B1}", "q"),
    ("Mã giảm giá {B1} là {PW}, dùng được đến hết tháng", "mã giảm giá {B1} là gì", "{PW}", "q"),
    ("Anh {P1} ngồi bàn số 12, gần cửa sổ tầng 4", "anh {P1} ngồi bàn số mấy", "{P1}", "q"),
    ("Bác sĩ hẹn {P1} tái khám lúc 10h sáng ngày 18/12 ở phòng khám {B1}", "{P1} tái khám lúc mấy giờ", "{P1}", "q"),
    ("Link đồ án nhóm {B1} để trong thư mục chung của {P1}", "link đồ án nhóm {B1} ở đâu", "{B1}", "q"),
    ("Phòng họp {B1} đặt được tối đa 14 người", "phòng họp {B1} chứa được bao nhiêu người", "{B1}", "q"),
    ("Tiền điện tháng này của căn hộ {B1} là 1tr4", "tiền điện tháng này căn hộ {B1} bao nhiêu", "{B1}", "q"),
    ("mật khẩu máy chiếu phòng {B1} là {PW}", "mật khẩu máy chiếu phòng {B1} là gì", "{PW}", "g"),
    ("xe của {P1} đỗ ở hầm B2 trụ số {B1}", "xe của {P1} đỗ ở đâu", "{P1}", "g"),
    ("ca sĩ {P1} sẽ biểu diễn ở đêm nhạc {B1} lúc 8h tối", "{P1} biểu diễn mấy giờ ở đêm nhạc {B1}", "{P1}", "g"),
    ("hợp đồng thuê kho {B1} hết hạn ngày 30/6 nha", "hợp đồng thuê kho {B1} hết hạn ngày nào", "{B1}", "g"),
]
CODESW = [
    ("hạn nộp báo cáo quý 3 dự án {B1} là thứ Sáu tuần sau", "deadline report Q3 project {B1} khi nào"),
    ("buổi họp khách hàng {B1} dời sang 10h sáng mai, phòng họp lớn", "meeting với client {B1} mấy giờ, room nào"),
    ("anh {P1} đã duyệt bản thiết kế trang chủ {B1}", "{P1} approve design homepage {B1} chưa"),
    ("mình phải làm thêm giờ tối thứ Năm để kịp đợt giao hàng cho {B1}", "OT thứ 5 cho {B1} đúng ko"),
    ("đặt phòng họp tầng 6 cho buổi đào tạo {B1} rồi nhé", "book room tầng 6 cho training {B1} xong chưa"),
    ("nhớ gửi bảng báo giá cho {B1} trước 5h chiều", "send quotation cho {B1} before 5pm nhớ ko"),
    ("chị {P1} chuyển sang bộ phận kinh doanh từ đầu tháng", "{P1} qua team sale từ khi nào"),
    ("khách {B1} phản hồi là họ chưa hài lòng với bản demo", "feedback của {B1} về demo thế nào"),
    ("ngày làm việc đầu tiên của nhân viên mới {P1} là 2/1, cần chuẩn bị máy tính", "onboard {P1} start ngày nào, cần setup laptop"),
    ("kế hoạch chiến dịch {B1} bị hoãn sang quý sau do thiếu ngân sách", "plan campaign {B1} bị delay hả, vì sao"),
    ("{P1} đã hủy chuyến công tác đi {B1}", "{P1} cancel trip đi {B1} à"),
    ("bản cập nhật tiến độ dự án {B1} nằm trong thư mục chung, {P1} đã chia sẻ", "progress update project {B1} ở folder nào, {P1} share rồi"),
    ("mục tiêu doanh số tháng này của nhóm {B1} là 900 triệu", "KPI sale tháng này team {B1} bao nhiêu"),
    ("meeting note {B1} do {P1} viết, đã share lên drive", "biên bản cuộc họp {B1} ai viết, đưa lên đâu"),
    ("pls send me the file {B1} b4 5pm, {P1} cần review", "{P1} cần xem tệp {B1} lúc nào"),
    ("feedback của {B1}: ok về price nhưng chưa ok phần timeline, {P1} sẽ call lại", "khách {B1} không đồng ý phần nào, ai gọi lại cho họ"),
]
TEENQ = [
    ("chìa khóa kho {B1} anh {P1} đang giữ, lát ảnh mang xuống", "ai giữ chìa khóa kho {B1} z, ko thấy đâu", "{B1}"),
    ("bây giờ cả nhóm tập trung ở sảnh tòa {B1} nhé", "bh mn tập trung ở đâu z, tòa {B1} hả", "{B1}"),
    ("{P1} không đi được tiệc {B1} vì phải về quê", "sao {P1} ko đi tiệc {B1} đc z", "{P1}"),
    ("chị {P1} nói tuần sau mới có kết quả xét nghiệm", "c {P1} ns bh có kq xét nghiệm z", "{P1}"),
    ("điện thoại của {P1} bị mất ở trạm xe buýt {B1}", "đt {P1} mất ở đâu z, trạm {B1} hả", "{P1}"),
    ("số nội bộ của phòng {B1} là ext {N}{N1}", "sdt nội bộ phòng {B1} là j z", "ext {N}{N1}"),
    ("ngày mai {P1} nhắn tin cho khách {B1} nhé, đừng gọi", "mai ai ib khách {B1} z", "{B1}"),
    ("chi phí đổ xăng chuyến đi {B1} tổng cộng 640k, {P1} ứng trước", "xăng chuyến {B1} hết bn z, ai ứng trc", "{B1}"),
    ("tối nay anh em ăn lẩu ở quán {B1}, {P1} đặt bàn lúc 7h", "tối nay ae ăn lẩu quán {B1} mấy h z", "{B1}"),
    ("mật khẩu máy chấm công của {B1} đã đổi, hỏi chị {P1} nhé", "mk máy chấm công {B1} đổi r à, hỏi ai z", "{B1}"),
    ("anh {P1} nói hạn nộp slide {B1} dời sang thứ 6", "a {P1} ns dl slide {B1} dời qua hôm nào z", "{B1}"),
    ("hàng của {B1} về kho rồi, nhưng thiếu 3 thùng", "hàng {B1} về r chưa, thiếu j ko", "{B1}"),
    ("{P1} vừa nghỉ việc ở công ty {B1}, tuần sau bàn giao", "{P1} nghỉ ở cty {B1} thật ko, bh bàn giao", "{P1}"),
    ("{P1} đã mua vé xem phim {B1} suất 20h", "ai mua vé phim {B1} r, suất mấy h z", "{B1}"),
    ("xe giao hàng {B1} bị hỏng nên chiều mới tới", "xe {B1} chưa tới à, bao giờ tới z", "{B1}"),
    ("phòng khám {B1} nghỉ thứ 7 và chủ nhật", "pk {B1} có làm cuối tuần ko z", "{B1}"),
]
VAGUE = [
    ("a {P1} gửi file logo {B1} r nha e", "ổng gửi cái file logo hôm bữa chưa", "logo"),
    ("e ơi brochure {B1} bản in thử bị lệch màu, nhắn bả sửa giúp", "bả sửa cái bản mẫu lệch màu chưa", "brochure"),
    ("standee {B1} chị {P1} cất ở góc phòng kho, ai cần thì lấy", "cái hình to đứng ở sảnh bả cất đâu rồi", "standee"),
    ("voucher {B1} của e còn hạn tới cuối tháng, a {P1} xài chưa", "cái phiếu giảm giá ảnh còn xài đc ko", "voucher"),
    ("mascot {B1} thuê hết 2tr/ngày, bên {P1} báo giá r", "bộ đồ thú to thuê bao nhiêu 1 ngày", "mascot"),
    ("áp phích sự kiện {B1} anh {P1} duyệt bản số 3 r", "ổng duyệt bản nào rồi nhỉ, cái tờ dán tường", "áp phích"),
    ("set quà tết {B1} đã đóng xong 120 hộp", "mấy hộp tết đóng xong chưa, bao nhiêu hộp", "quà tết"),
    ("máy khoan của {P1} để quên ở nhà {B1} nha", "cái máy đục lỗ ổng để quên đâu", "máy khoan"),
    ("bảng hiệu cửa hàng {B1} lắp xong hôm qua rồi", "tấm biển trước tiệm làm xong chưa", "bảng hiệu"),
    ("đồng phục team {B1} size M thiếu 5 cái, {P1} đặt thêm", "áo cả nhóm thiếu size nào, bả đặt thêm chưa", "đồng phục"),
    ("ổ cứng ngoài {B1} ảnh để trong ngăn kéo bàn {P1}", "cái ổ lưu trữ ngoài đâu rồi", "ổ cứng ngoài"),
    ("bánh kem {B1} đặt lúc 3h chiều, {P1} đi lấy", "ai đi lấy cái bánh sinh nhật", "bánh kem"),
    ("máy ảnh {B1} cho {P1} mượn đến thứ 2", "cái máy chụp hình mượn tới bao giờ", "máy ảnh"),
    ("xe nâng kho {B1} hết xăng, {P1} đã báo bảo trì", "mấy cái xe trong kho sao ko chạy", "xe nâng"),
    ("kệ sách {B1} giao sáng mai, {P1} ở nhà nhận", "cái tủ để sách khi nào giao, ai nhận", "kệ sách"),
    ("tem nhãn {B1} in sai mã vạch, a {P1} đã yêu cầu in lại", "cái nhãn dán bị sai r, ổng bắt in lại chưa", "tem nhãn"),
]
# (old, new, query, fact_new)
CORRECT = [
    ("{P1} đi lấy hợp đồng {B1} thứ 6 nha", "đổi plan nha, {P2} đi lấy hợp đồng {B1} chứ ko phải {P1}", "ai đi lấy hợp đồng {B1} thứ 6", "{P2}"),
    ("họp dự án {B1} lúc 9h sáng mai", "sửa lại giờ họp dự án {B1}: 14h chiều mai, ko phải 9h nha", "mai mấy giờ họp dự án {B1}", "sửa lại giờ họp dự án {B1}"),
    ("tiền cọc phòng {B1} là 3tr", "nhầm r, tiền cọc phòng {B1} là 5tr chứ ko phải 3tr", "tiền cọc phòng {B1} bao nhiêu", "phòng {B1} là 5tr"),
    ("sinh nhật {P1} tổ chức ở nhà hàng {B1}", "đổi địa điểm sinh nhật {P1}, qua quán {B2} nha, {B1} full bàn r", "sinh nhật {P1} tổ chức ở đâu", "{B2}"),
    ("{P1} sẽ gửi báo giá {B1} vào thứ Hai", "báo giá {B1} dời qua thứ Tư nhé, {P1} bận", "khi nào {P1} gửi báo giá {B1}", "báo giá {B1} dời qua thứ Tư"),
    ("mật khẩu wifi tầng 5 {B1} là {PW}", "wifi tầng 5 {B1} đổi pass r, pass mới là {PW2}", "pass wifi tầng 5 {B1} là gì", "{PW2}"),
    ("kho {B1} giao hàng 100 thùng", "sorry nhầm, đơn kho {B1} chỉ 80 thùng thôi", "kho {B1} giao bao nhiêu thùng", "đơn kho {B1} chỉ 80 thùng"),
    ("hạn nộp hồ sơ {B1} là 20/12", "gia hạn nộp hồ sơ {B1} tới 5/1 nha mn", "hạn nộp hồ sơ {B1}", "gia hạn nộp hồ sơ {B1}"),
    ("{P1} sẽ lái xe đưa khách {B1} ra sân bay", "ko phải {P1}, {P2} mới là người đưa khách {B1} ra sân bay", "ai đưa khách {B1} ra sân bay", "{P2} mới là"),
    ("phòng họp {B1} đặt lúc 10h", "hủy 10h, book lại phòng họp {B1} lúc 15h nha", "phòng họp {B1} đặt lúc nào", "book lại phòng họp {B1}"),
    ("giá gói {B1} là 20tr", "update giá gói {B1} thành 18tr sau khi trừ chiết khấu", "giá gói {B1} hiện tại bao nhiêu", "giá gói {B1} thành 18tr"),
    ("chuyến bay đi {B1} cất cánh 6h sáng", "hãng báo chuyến {B1} lùi lại 9h20, ko phải 6h", "chuyến bay {B1} cất cánh mấy giờ", "chuyến {B1} lùi lại 9h20"),
    ("ngày giao xe {B1} là 12/3", "xe {B1} giao sớm hơn, ngày 8/3 nhé", "xe {B1} giao ngày nào", "xe {B1} giao sớm hơn"),
    ("{P1} phụ trách chăm sóc khách {B1}", "chuyển khách {B1} sang cho {P2} phụ trách nha, {P1} qua dự án khác", "ai phụ trách khách {B1}", "chuyển khách {B1} sang"),
    ("bữa trưa team {B1} ăn cơm tấm", "đổi món, trưa nay team {B1} ăn bún bò nha, ko cơm tấm", "trưa nay team {B1} ăn gì", "team {B1} ăn bún bò"),
    ("tiền công dự án {B1} trả vào ngày 5", "{P1} báo tiền công dự án {B1} trả trễ, ngày 10 mới có", "tiền công dự án {B1} khi nào trả", "báo tiền công dự án {B1}"),
]
# (query, terms that must appear nowhere in the corpus)
UNANS = [
    ("bảo hiểm xe Vespa của sếp hết hạn khi nào", ["vespa"]),
    ("vé đi Kyoto đặt chưa", ["kyoto"]),
    ("lớp Zumba tối thứ 4 mấy giờ", ["zumba"]),
    ("ai đặt kombucha cho văn phòng vậy", ["kombucha"]),
    ("xe Tesla của giám đốc sạc ở đâu", ["tesla"]),
    ("ho so visa Uc cua chi Lan nop chua", ["visa uc"]),
    ("con Mochi hôm qua đi khám thú y chưa", ["mochi"]),
    ("ai đi xăm hình hôm qua z", ["xăm"]),
    ("ai mua bitcoin hôm qua vậy", ["bitcoin"]),
    ("đăng ký marathon 21km chưa", ["marathon"]),
    ("thẻ Techcombank mới ai làm vậy", ["techcombank"]),
    ("tour Kon Tum tháng sau đi mấy người", ["kon tum"]),
    ("sân pickleball đặt giờ nào", ["pickleball"]),
    ("khi nào thi chứng chỉ PMP", ["pmp"]),
    ("check lịch thầy phong thủy xem ngày khai trương", ["phong thủy"]),
    ("laptop Framework của team dev giao chưa", ["framework"]),
]


def _build(n_chunks, seed):
    r = random.Random(seed)
    RESERVED.clear()
    names = [f"{g} {s}" for g in NAME_GIVEN for s in NAME_SUFFIX]
    r.shuffle(names)
    brands = BRANDS + [f"{a} {b}" for a in BR_A for b in BR_B]
    r.shuffle(brands)
    used = set()

    def code():
        while True:
            c = f"{PREF[r.randrange(5)]}-{r.randint(2023, 2026)}-{r.randint(1, 9999):04d}"
            if c not in RESERVED:
                RESERVED.add(c)
                return c

    def pw():
        while True:
            p = f"{r.choice(PWWORDS)}#{r.randint(1000, 9999)}"
            if p not in used:
                used.add(p)
                RESERVED.add(p)
                return p

    def num():  # 5-digit unique chunk; "{N}{N1}" gives a 10-digit unique number
        while True:
            p = str(r.randint(10000, 99999))
            if p not in used:
                used.add(p)
                return p

    ctx = {"P": names.pop, "B": brands.pop, "C": code, "PW": pw, "N": num}
    f = _F()
    f.r = r
    plant, queries, facts = [], [], []  # plant: chunk texts in pre-shuffle order

    def add(text):
        plant.append(text)
        return len(plant) - 1

    def q(typ, text, gold, fact, stale=None, stale_fact=None, terms=None):
        queries.append({"type": typ, "text": text, "gold": gold, "stale": stale})
        facts.append({"fact": fact, "stale_fact": stale_fact, "terms": terms})

    L = lambda: _P(ctx)
    for g, qq, ft in WARMUP:
        s = L()
        q("warmup", qq.format_map(s), add(g.format_map(s)), ft.format_map(s))
    warm = queries[:]
    wf = facts[:]
    queries.clear()
    facts.clear()
    for g, qq, ft in EXACT * 2:
        s = L()
        q("exact_code", qq.format_map(s), add(g.format_map(s)), ft.format_map(s))
    for g, qq, ft in PARAPHRASE:
        s = L()
        q("paraphrase", qq.format_map(s), add(g.format_map(s)), ft.format_map(s))
    for g, qq, ft in LONGFACT:
        s = L()
        fact_sentence = g.format_map(s)
        q("long_chunk_fact", qq.format_map(s), add(long_chunk(r, f, fact_sentence)), ft.format_map(s))
    for g, qq, ft, side in NODIAC:
        s = L()
        g, qq, ft = g.format_map(s), qq.format_map(s), ft.format_map(s)
        if side == "q":
            qq = nd(qq)
        else:
            g, ft = nd(g), nd(ft)
        q("no_diacritics", qq, add(g), ft)
    for g, qq in CODESW:
        s = L()
        q("code_switch", qq.format_map(s), add(g.format_map(s)), s["B1" if "{B1}" in g else "P1"])
    for g, qq, ft in TEENQ:
        s = L()
        q("teencode", qq.format_map(s), add(g.format_map(s)), ft.format_map(s))
    for g, qq, ft in VAGUE:
        s = L()
        q("vague_context", qq.format_map(s), add(g.format_map(s)), ft)
    for old, new, qq, ft in CORRECT:
        s = L()
        o = old.format_map(s)
        i_old = add(o)
        n = new.format_map(s)
        i_new = add(n)
        q("correction", qq.format_map(s), i_new, ft.format_map(s), stale=i_old, stale_fact=o)
    for qq, terms in UNANS:
        q("unanswerable", qq, None, None, terms=terms)
    queries[:0] = warm
    facts[:0] = wf
    n_fill = n_chunks - len(plant)
    assert n_fill >= 0, "n_chunks too small for planted items"
    corpus = plant
    for _ in range(n_fill):
        x = r.random()
        if x < .05:
            corpus.append(long_chunk(r, f))
        elif x < .24:
            corpus.append(short_reply(r))
        else:
            corpus.append(topic_msg(r, f))
    n = len(corpus)
    order = list(range(n))
    r.shuffle(order)
    pos = [0] * n
    for new, old in enumerate(order):
        pos[old] = new
    for qq in queries:  # keep stale before its correction (chat order)
        s, g = qq["stale"], qq["gold"]
        if s is not None and pos[s] > pos[g]:
            pos[s], pos[g] = pos[g], pos[s]
            order[pos[s]], order[pos[g]] = s, g
    out_q = [{"type": qq["type"], "text": qq["text"],
              "gold": None if qq["gold"] is None else pos[qq["gold"]],
              "stale": None if qq["stale"] is None else pos[qq["stale"]]} for qq in queries]
    return [corpus[o] for o in order], out_q, facts


FACTS = []  # parallel to the queries of the last build(): distinctive substrings for the self-check


def build(n_chunks: int, seed: int = 11):
    """corpus: one string per chunk; queries: {"type","text","gold","stale"} (3 warmup first)."""
    global FACTS
    corpus, queries, FACTS = _build(n_chunks, seed)
    return corpus, queries


# ---------- self-check ----------
def _fold(s):
    return nd(s).lower()


def wcount(hay, needle):
    """occurrences of needle at word boundaries (hay and needle already folded/lowercased)"""
    if hay.count(needle) <= 1:
        return hay.count(needle)
    return len(re.findall(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", hay))


def check(n=10000):
    corpus, queries = build(n)
    assert len(corpus) == n and len(queries) == len(FACTS)
    assert [q["type"] for q in queries[:3]] == ["warmup"] * 3
    big = "\n".join(corpus)
    bigf = _fold(big)
    cnt = Counter(corpus)
    for q, ft in zip(queries, FACTS):
        g, s = q["gold"], q["stale"]
        if q["type"] == "unanswerable":
            assert g is None and s is None
            for t in ft["terms"]:
                assert wcount(bigf, _fold(t)) == 0, ("unanswerable term present", t)
            continue
        assert 0 <= g < n, q
        assert cnt[corpus[g]] == 1, ("gold text not unique", q)
        assert ft["fact"] in corpus[g], ("fact missing in gold", q, ft)
        assert big.count(ft["fact"]) == 1, ("fact not unique", ft["fact"], q)
        # vague nouns are common words once accents are gone ("máy ảnh" ~ "mấy anh"): raw check only
        assert q["type"] == "vague_context" or wcount(bigf, _fold(ft["fact"])) == 1, ("folded fact not unique", ft["fact"], q)
        if q["type"] == "correction":
            assert s is not None and 0 <= s < g and s != g, q
            assert cnt[corpus[s]] == 1 and big.count(ft["stale_fact"]) == 1, q
        else:
            assert s is None
    assert unicodedata.normalize("NFC", big) == big, "non-NFC text"
    c2, q2 = build(n)
    assert c2 == corpus and q2 == queries, "not deterministic"
    return corpus, queries


def stats(corpus):
    n = len(corpus)
    ws = [c.split() for c in corpus]
    long_ = sum(len(w) >= 150 for w in ws)
    short = sum(len(w) <= 3 and not any(ch.isdigit() for ch in c) for w, c in zip(ws, corpus))
    nodiac = sum(len(w) >= 3 and len(w) < 150 and not _HAS_DIAC.search(c) for w, c in zip(ws, corpus))
    eng = re.compile(r"\b(deadline|meeting|check|confirm|feedback|report|team|inbox|rep|update|plan|task|"
                     r"slide|file|ot|book|cancel|sale|kpi|onboard|join|call|note|share|approve|pls|"
                     r"send|thanks|ok|will|the|invoice|review|sync|got it|sorry|late|traffic|any)\b", re.I)
    en = sum(bool(eng.search(c)) and len(w) < 150 for w, c in zip(ws, corpus))
    pc = lambda x: f"{100 * x / n:.1f}%"
    print(f"no diacritics (>=3 words): {pc(nodiac)} | with English words: {pc(en)} | "
          f"short replies (<=3 words): {pc(short)} | long chunks: {pc(long_)}")


if __name__ == "__main__":
    corpus, queries = check(10000)
    print("self-check PASSED (10,000 chunks)")
    stats(corpus)
    print("query counts:", dict(Counter(q["type"] for q in queries)))
    rr = random.Random(5)
    print("\n--- 30 random corpus samples ---")
    for i in rr.sample(range(len(corpus)), 30):
        print(" ", corpus[i][:160].replace("\n", " "))
    print("\n--- 2 examples per type ---")
    seen = Counter()
    for q in queries:
        if seen[q["type"]] < 2:
            seen[q["type"]] += 1
            print(f"[{q['type']}] Q: {q['text']}")
            print("   gold:", None if q["gold"] is None else corpus[q["gold"]][:200] + (" ..." if q["gold"] is not None and len(corpus[q["gold"]]) > 200 else ""))
            if q["stale"] is not None:
                print("   stale:", corpus[q["stale"]])
    t = time.time()
    big, bq = build(1_000_000)
    dt = time.time() - t
    print(f"\nbuilt 1,000,000 chunks in {dt:.1f}s; queries={len(bq)}")
    bj = "\n".join(big)
    bf = _fold(bj)
    for q, ft in zip(bq, FACTS):
        if q["type"] == "unanswerable":
            assert all(wcount(bf, _fold(x)) == 0 for x in ft["terms"]), ft
        else:
            assert bj.count(ft["fact"]) == 1 and (q["type"] == "vague_context" or wcount(bf, _fold(ft["fact"])) == 1), ft
            if q["stale"] is not None:
                assert q["stale"] < q["gold"] and bj.count(ft["stale_fact"]) == 1
    print("1M uniqueness / unanswerable check PASSED")
    stats(big)

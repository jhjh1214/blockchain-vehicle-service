from db.models import db, User


def find_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def find_by_email(email: str) -> User | None:
    return User.query.filter_by(email=email).first()


def find_by_blockchain_address(address: str) -> User | None:
    return User.query.filter_by(blockchain_address=address).first()


def find_all_by_role(role: str) -> list:
    return User.query.filter_by(role=role).all()


def create(email: str, password: str, role: str, name: str, phone: str,
           blockchain_address: str) -> User:
    user = User(email=email, role=role, blockchain_address=blockchain_address,
                name=name, phone=phone or '')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

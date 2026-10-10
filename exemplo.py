"""Exemplo rápido: cria uma bardo, sobe para o nível 2 e mostra ficha e linha do tempo.

Rode com:  python exemplo.py
"""

from motor import Biblioteca, Criacao, Escolha, Opcao, Personagem, SubidaDeNivel, Traco

bib = Biblioteca()

lira = Personagem(bib, Criacao(
    nome="Lira",
    classe="core_class_bard",
    subclasse="core_subclass_troubadour",
    ancestralidade="core_ancestry_clank",
    comunidade="core_community_highborne",
    tracos={Traco.PRESENCA: 2, Traco.AGILIDADE: 1, Traco.CONHECIMENTO: 1,
            Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1},
    experiencias=["Diplomata", "Cantora de taverna"],
    cartas=["core_domain_card_inspirational_words", "core_domain_card_book_of_ava"],
))

print("Opções para o nível 2:")
for o in lira.opcoes_disponiveis():
    print(f"  tier {o['tier']}  {o['opcao'].value:<14} restam {o['restantes']}")

lira.subir_de_nivel(SubidaDeNivel(
    nivel=2,
    escolhas=[Escolha(Opcao.TRACOS, tracos=(Traco.PRESENCA, Traco.AGILIDADE)),
              Escolha(Opcao.EVASAO)],
    carta="core_domain_card_tell_no_lies",
    nova_experiencia="Ladina de palco",
))

f = lira.ficha()
print(f"\n{f.nome} — nível {f.nivel} | Evasão {f.evasao} | PV {f.pv_max} | "
      f"Estresse {f.estresse_max} | Proficiência {f.proficiencia}")
print("Traços:", {t.rotulo: v for t, v in f.tracos.items()})
print("Experiências:", f.experiencias)

print("\nLinha do tempo:")
for evento in lira.linha_do_tempo()[:3]:
    print(f"  [{evento['status']}] {evento['titulo']}")
    for item in evento["itens"]:
        print(f"      - {item}")
